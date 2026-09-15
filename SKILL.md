---
name: thetaio-grok-search
description: 通过 ThetaIO 网关调用 Grok 的实时搜索能力，检索 X（Twitter）站内帖子/用户 或 公开互联网网页，并返回原始链接作为信源。当用户需要查"某人最近在 X 上说了什么"、"某话题在 X/网上的最新动态"、"带真实链接的最新资讯/舆情"、或任何需要联网搜索 X 或网络的问题时使用。触发词：搜索X、搜推特、搜推、查某人最近推文、X上怎么说、最新动态、联网搜索、web search、x search、grok search。
license: MIT
compatibility: 需要 Python 3.8+（仅标准库）与网络访问。可选环境变量 THETAIO_API_KEY 提供网关密钥。
---

# ThetaIO Grok 搜索

用 Grok 的 server-side 搜索工具，实时检索 **X 站内** 或 **公开网络**，返回带原始链接的结果。

## 何时使用

- 查某人（如 @elonmusk、OpenAI 员工）最近在 X 上发了什么 / 回复了什么
- 查某话题在 X 或全网的最新动态、舆情、新闻，并要求真实链接
- 需要"搜索结果 + 信源链接"的场景；不要用于纯对话或离线知识问题

## 前置条件

- 密钥：环境变量 `THETAIO_API_KEY`（或 `THETAIO_KEY`）。缺失时脚本会报错提示。
- 网关：默认 `https://api.thetaio.tech`，可用 `THETAIO_BASE_URL` 覆盖。
- 模型：默认 `grok-4.3`（**唯一推荐**）。不要用 `grok-4.5`，它两个搜索工具都会 400。

## 安装

```bash
git clone <repo-url> thetaio-grok-search
export THETAIO_API_KEY="sk-..."     # Windows: set THETAIO_API_KEY=sk-...
```

把本目录放到客户端的 skills 目录（如 `~/.config/opencode/skills/` 或 `~/.claude/skills/`）即可被自动发现。

## 用法

```bash
# X 站内搜索（默认）
python scripts/grok_search.py "latest posts from @elonmusk" --show-tools

# 公开网络搜索
python scripts/grok_search.py "latest AI news with links" --tool web

# 流式 + 展示每次工具调用过程
python scripts/grok_search.py "what did OpenAI ship this week" --stream --show-tools

# 输出原始 JSON
python scripts/grok_search.py "posts from @thsottiaux" --json
```

## 关键规则（务必遵守）

1. **必须校验是否真的搜了**：响应 `usage.server_side_tool_usage_details.x_search_calls`（或 `web_search_calls`）必须 > 0。脚本会打印"搜索调用次数"；若为 0，说明模型没真正调用工具，结果可能是编造的，**不要采信**。
2. **信源在 `annotations` 里**，不在 `results` 字段。脚本已自动提取 `output[].content[].annotations[].url_citation.url`。
3. **必须引用原始链接**回答用户；不要把无链接的内容当事实交付。
4. **独立端点** `/v1/x_search`、`/v1/web_search` 只对 `grok` 平台 group 的 Key 可用；`openai` 平台 group 会返回 404。本 skill 统一走 `/v1/responses` + `tools`，兼容两者。
5. 不要加 `"include": ["x_search_call.action.sources"]`，上游会 400。
6. 不要强制 `tool_choice: "required"`，部分模型组合会 400。

## 输出解析

非流式响应结构：

```jsonc
{
  "output": [
    { "type": "reasoning", "encrypted_content": "..." },
    { "type": "custom_tool_call", "name": "x_keyword_search",
      "input": "{\"query\":\"from:xai\",\"limit\":\"10\"}", "status": "completed" },
    { "type": "message",
      "content": [{ "type": "output_text", "text": "...",
        "annotations": [{ "type": "url_citation", "url": "https://x.com/..." }] }] }
  ],
  "usage": { "server_side_tool_usage_details": { "x_search_calls": 3 } }
}
```

流式（SSE）会逐次推送工具调用：`response.output_item.added`（`type=custom_tool_call`）→ `response.custom_tool_call_input.delta` → `response.custom_tool_call_input.done`，随后是 `response.output_text.delta` 与 `response.output_text.annotation.added`，最后 `response.completed`。用 `--stream --show-tools` 可实时看到每次 `x_keyword_search` / `x_user_search` / `x_semantic_search` 及其参数。

## 进阶

- 完整 API 规范、报错对照表、模型矩阵：见 `references/grok-search-api.md`
- 客户端调用模板（curl / Python）：见 `references/grok-search-api.md` 第 2、5、8 节
