# FigmaEval

论文 **FigmaEval: A Benchmark for Evaluating AI Agents in Professional UI Design** 的官方实现。

FigmaEval 用于评估 AI 智能体在原生、可编辑 Figma 环境中的界面设计能力。基准包含 84 个任务、783 个界面；本仓库提供设计生成、自动评分和人工盲评代码。

## 代码结构

| 路径 | 内容 |
|---|---|
| `scripts/claude_code_harness.py` | 设计生成与自动评分 |
| `server/figma_mcp_stdio_proxy.py` | Figma MCP 工具接入 |
| `benchmarks/rubrics/` | 评分量表 |
| `arena/`、`server/benchmark_arena.mjs` | 人工盲评界面与服务 |
| `examples/` | 配置示例 |
| `tests/` | 测试代码 |

## 安装

环境：Linux、Python 3.11+、Node.js 22.16+。

```bash
npm ci
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
npm install -g @anthropic-ai/claude-code
```

## 使用

参考 `examples/inference.example.json` 和 `examples/judges.example.json`，配置模型 API、Figma OAuth 和任务文件，将配置保存在 `private/`。

```bash
# 生成设计
npm run paper:inference -- \
  --config private/inference.json --output outputs/inference

# 自动评分
npm run paper:judge -- \
  --config private/judges.json \
  --from-inference outputs/inference/BATCH_DIRECTORY \
  --output outputs/judges
```

将 `BATCH_DIRECTORY` 替换为生成设计时输出的批次目录。

人工评测界面演示：

```bash
npm run demo
```

启动后，在另一终端执行 `cat outputs/arena-demo/access.json` 查看访问码，并打开[本地页面](http://127.0.0.1:18186)。演示使用合成数据。

本仓库不包含基准任务数据与论文评测结果。
