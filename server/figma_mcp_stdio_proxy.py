#!/usr/bin/env python3
"""Expose the authenticated remote Figma MCP as a filtered local stdio server."""

import json
import os
import asyncio

import anyio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from figma_mcp_budget import wait_for_slot, record_result, begin_request, record_transport_error
from figma_mcp_target import assert_assigned_file
from figma_async_execution import await_async_iife


FIGMA_MCP_URL = os.environ.get("FIGMA_MCP_URL", "https://mcp.figma.com/mcp")
AUTH_FILE = os.environ["FIGMA_MCP_AUTH_FILE"]
ALLOWED_TOOLS = {
    name.strip()
    for name in os.environ.get("FIGMA_MCP_ALLOWED_TOOLS", "").split(",")
    if name.strip()
}
# 「对话修改」专用：把模型的每段 use_figma 脚本强制钉在指定页面上（不设这个变量时完全不生效）。
# 2026-09-21 真实事故：平台刚把「工作页」插到首位，模型的会话紧接着开始，Figma 侧页面顺序还没同步，
# use_figma 默认落在了旧首页（原稿）——模型全程只用 figma.currentPage、完全守规矩，却把原稿整页改了色。
# 所以不能依赖"默认落在哪页"：脚本执行前先按名字切到工作页，找不到就抛错（宁可这次调用失败，也不改错页）。
PIN_PAGE = os.environ.get("FIGMA_MCP_PIN_PAGE", "").strip()
PIN_PAGE_ID = os.environ.get("FIGMA_MCP_PIN_PAGE_ID", "").strip()
AWAIT_ASYNC_IIFE = os.environ.get("FIGMA_MCP_AWAIT_ASYNC_IIFE", "") == "1"
ERROR_GUIDANCE = os.environ.get("FIGMA_MCP_ERROR_GUIDANCE", "") == 'figma-api-guidance/v1'
# 单次远端调用的总时限（秒）。2026-11-01 起 Figma 远端 get_screenshot 间歇性"不返回也不报错"：
# httpx 的 120s 是读空闲超时，被流式心跳续命，不会触发；Claude Code 要等 1800s 才中止，
# 直连模式（GPT）则一直等到整题超时。10case 28 条超时里 27 条是这个原因。
# 实测 1 万多次成功调用最长 15s，120s 足够宽；卡死时尽快把错误交给模型，让它重试或换方式。
CALL_TIMEOUT = float(os.environ.get("FIGMA_MCP_CALL_TIMEOUT", "120"))


def pin_page_prelude(page_name: str, page_id: str = "") -> str:
    if page_id:
        return (
            "{ const __pin=figma.root.children.find(p=>p.id==="+json.dumps(page_id)+");\n"
            "if(!__pin)throw Error('Assigned Workspace page ID is missing; no canvas edits permitted');\n"
            "await __pin.loadAsync();if(figma.currentPage.id!==__pin.id)await figma.setCurrentPageAsync(__pin); }\n"
        )
    return (
        "{ const __pin = figma.root.children.find((p) => p.name === " + json.dumps(page_name, ensure_ascii=False) + ");\n"
        "  if (!__pin) throw new Error(" + json.dumps(f"找不到页面「{page_name}」，为避免改错页面，本次调用已中止；请稍后重试", ensure_ascii=False) + ");\n"
        "  if (figma.currentPage.id !== __pin.id) await figma.setCurrentPageAsync(__pin); }\n"
    )


def pin_use_figma(name: str, arguments: dict) -> dict:
    if AWAIT_ASYNC_IIFE and name == 'use_figma' and isinstance(arguments,dict):
        arguments={**arguments,'code':await_async_iife(arguments.get('code') or '')}
    if not (PIN_PAGE or PIN_PAGE_ID) or name != "use_figma" or not isinstance(arguments, dict):
        return arguments
    return {**arguments, "code": pin_page_prelude(PIN_PAGE, PIN_PAGE_ID) + str(arguments.get("code") or "")}


server = Server("figma-authenticated-proxy")
_pooled_session = None
_pooled_authorization = None
_pooled_lock = asyncio.Lock()


def auth_headers():
    with open(AUTH_FILE, encoding="utf-8") as handle:
        token = json.load(handle)["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def with_figma(action):
    mode = os.environ.get('FIGMA_MCP_HTTP_TRANSPORT', 'pooled')
    if mode == 'pooled':
        from figma_network import FigmaRpcSession, FigmaNetworkError
        global _pooled_session, _pooled_authorization
        authorization = auth_headers()['Authorization']
        async with _pooled_lock:
            if _pooled_session is None or _pooled_authorization != authorization:
                if _pooled_session is not None:
                    await _pooled_session.close()
                _pooled_session = FigmaRpcSession(FIGMA_MCP_URL, authorization, CALL_TIMEOUT)
                _pooled_authorization = authorization
            try:
                await _pooled_session.initialize()
                return await action(_pooled_session)
            except FigmaNetworkError as error:
                # A safe failure means the request was not sent, or the action
                # is read-only. Never replay an ambiguous use_figma write.
                if not error.safe_to_retry:
                    raise
                await _pooled_session.close()
                _pooled_session = None
                from figma_mcp_curl import CurlSession
                fallback = CurlSession(FIGMA_MCP_URL, auth_headers(), CALL_TIMEOUT)
                await fallback.initialize()
                return await action(fallback)
    if mode == 'curl':
        from figma_mcp_curl import CurlSession
        session = CurlSession(FIGMA_MCP_URL, auth_headers(), CALL_TIMEOUT)
        await session.initialize()
        return await action(session)
    async with httpx.AsyncClient(headers=auth_headers(), timeout=120) as client:
        async with streamable_http_client(
            FIGMA_MCP_URL,
            http_client=client,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                return await action(session)


@server.list_tools()
async def list_tools():
    result = await with_figma(lambda session: session.list_tools())
    if not ALLOWED_TOOLS:
        return result.tools
    return [tool for tool in result.tools if tool.name in ALLOWED_TOOLS]


@server.call_tool(validate_input=True)
async def call_tool(name, arguments):
    if ALLOWED_TOOLS and name not in ALLOWED_TOOLS:
        raise ValueError(f"Figma tool is not enabled for this session: {name}")
    assert_assigned_file(name, arguments, os.environ.get("FIGMA_MCP_ASSIGNED_FILE_KEY", ""))
    arguments = pin_use_figma(name, arguments)
    await wait_for_slot(name)
    request = begin_request(name, arguments.get("fileKey"))
    try:
        with anyio.fail_after(CALL_TIMEOUT):
            result = await with_figma(lambda session: session.call_tool(name, arguments))
    except BaseException as error:
        record_transport_error(request, error)
        if isinstance(error, TimeoutError):
            hint = "；use_figma 的修改可能已生效也可能没有，重试前请先读取当前状态" if name == "use_figma" else "，可以直接重试"
            raise RuntimeError(f"Figma 远端 {name} 在 {CALL_TIMEOUT:.0f} 秒内没有响应，本次调用已中止{hint}") from None
        raise
    # One logical tool call makes one remote request. Resource recovery belongs
    # to the account scheduler, not an invisible per-call retry loop.
    record_result(name, result, request)
    if ERROR_GUIDANCE:
        from figma_error_guidance import with_error_guidance
        result=with_error_guidance(result)
    return result


async def main():
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())
    finally:
        if _pooled_session is not None:
            await _pooled_session.close()


if __name__ == "__main__":
    import anyio

    anyio.run(main)
