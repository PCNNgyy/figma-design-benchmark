import { repairJsonQuotes } from "./cc_evaluation.mjs";
const parseJson = (text, fallback) => { try { return JSON.parse(text); } catch { return fallback; } };

export function extractClaudeResult(output) {
  const envelope = parseJson(String(output || "").trim(), null);
  if (typeof envelope === "string") return envelope;
  if (typeof envelope?.result === "string") return envelope.result;
  if (typeof envelope?.content === "string") return envelope.content;
  if (Array.isArray(envelope?.content)) {
    return envelope.content
      .map((entry) => typeof entry === "string" ? entry : entry?.text || "")
      .join("\n");
  }
  return String(output || "");
}

// 剥掉 Claude Code 的 JSON 外壳和 Markdown 代码块，再从正文里把 JSON 抠出来。
// 模型时不时会在 JSON 前后多写一句解释，只 JSON.parse 会整个失败。
export function parseClaudeJson(output) {
  const text = extractClaudeResult(output)
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();
  let parsed = parseJson(text, null);
  if (!parsed) {
    const objectStart = text.indexOf("{");
    const objectEnd = text.lastIndexOf("}");
    if (objectStart >= 0 && objectEnd > objectStart) {
      parsed = parseJson(text.slice(objectStart, objectEnd + 1), null);
    }
  }
  if (!parsed) {
    const arrayStart = text.indexOf("[");
    const arrayEnd = text.lastIndexOf("]");
    if (arrayStart >= 0 && arrayEnd > arrayStart) {
      parsed = parseJson(text.slice(arrayStart, arrayEnd + 1), null);
    }
  }
  if (!parsed) {
    // 最后一招：模型在正文里写了裸的英文双引号（引用界面文案时很常见），
    // 补上转义再试一次。修不好就还是返回 null，调用方各自兜底。
    const repaired = repairJsonQuotes(text);
    parsed = parseJson(repaired, null);
    if (!parsed) {
      const start = repaired.indexOf("{");
      const end = repaired.lastIndexOf("}");
      if (start >= 0 && end > start) parsed = parseJson(repaired.slice(start, end + 1), null);
    }
  }
  return parsed;
}
