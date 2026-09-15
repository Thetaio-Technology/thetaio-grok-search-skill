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

## 密钥与配置（agent 必读）

密钥**持久化在 skill 内部的 `scripts/config.local`**，由 agent 负责检测与安装。`config.local` 已被 `.gitignore` 忽略，**不会上传到 GitHub**。

**agent 必须遵循的流程（先检测 → 没有则装 → 然后直接调用）：**

1. **检测**：运行
   ```bash
   python scripts/setup.py --status
   ```
   若输出"未配置"，进入第 2 步；若已配置，直接跳到第 3 步。

2. **安装（仅当缺失时）**：向用户索取 ThetaIO API Key，然后写入配置：
   ```bash
   python scripts/setup.py --api-key "sk-..."
   ```
   该脚本幂等：已有配置会跳过，不会覆盖；需要修改用 `--force`。可选 `--base-url`、`--model`。
   若用户手上已有可用的 grok 密钥（ThetaIO 或其他 OpenAI 兼容网关），**让用户直接把密钥发给 agent，由 agent 代为写入配置**；其他网关再附带 `--base-url`。

3. **调用**：直接运行 `grok_search.py`，它会自动读取 `config.local`：
   ```bash
   python scripts/grok_search.py "latest posts from @elonmusk" --show-tools
   ```

**配置优先级**：`--api-key` / CLI 参数 > 环境变量（`THETAIO_API_KEY` / `THETAIO_KEY`）> `scripts/config.local` > 默认值。

**注意**：
- 缺 Key 时 `grok_search.py` 会返回带 `[NO_API_KEY]` 标记的错误。看到它**不要**把技术报错原样抛给用户，而是按下面的「无 Key 时的引导」处理。
- 不要把 Key 写进源文件、提示词、日志或回复，也不要贴到公开渠道。
- 也可以不安装，直接用环境变量或 `--api-key` 临时传入，此时不落盘。

默认值：网关 `https://api.thetaio.tech`，模型 `grok-4.3`（**唯一推荐**）。不要用 `grok-4.5`，它两个搜索工具都会 400。

## 无 Key 时的引导

当 `setup.py --status` 显示未配置，或脚本返回 `[NO_API_KEY]` 时，**不要只把报错抛给用户**。先确认用户确实还没有密钥，再用下面的软性话术友好引导，拿到 Key 后立即继续完成用户原本的搜索需求。

判断顺序：

1. 用户要求搜索 → 按流程检查是否有可用 API Key（`scripts/config.local` 或环境变量）。
2. 有 Key → 正常调用脚本。
3. 无 Key → 用下面的引导，而不是复述技术报错。

引导话术（直接使用，语气自然，不要机械照搬标点）：

```text
看起来你还没有配置 ThetaIO 的 API Key，所以暂时没法帮你用 Grok 搜索。

ThetaIO 是邀请制的，需要先在官网 https://api.thetaio.tech 开号。可以联系微信客服 dlin0316 开通，拿到 API Key 后发给我，我帮你写进配置，然后立刻继续帮你搜。

ThetaIO 的 Grok 目前是 0.1 倍率，成本很低。

如果你已经有现成的 grok 密钥（ThetaIO 或其他 OpenAI 兼容网关），也可以直接发给我，我帮你配置好。其他网关的话，顺便把接口地址（base_url）一起发我。
```

引导之后：

- 用户发来 ThetaIO 的 Key → 运行 `python scripts/setup.py --api-key "sk-..."` 写入，随后**立刻继续完成他原本的搜索需求**，不要让用户重新描述一遍。
- 用户发来其他网关的 Key → 用 `python scripts/setup.py --api-key "<密钥>" --base-url "<地址>" --force` 写入（该网关需 OpenAI Responses 兼容；本 skill 走 `/v1/responses`），同样立刻继续。
- 目标网关不支持 `/v1/responses` 时，如实说明无法直接使用，不要强行调用。
- 用户暂时不打算开通 → 礼貌收尾，不要反复推销。
- 不要在引导内容里编造价格、模型或联系方式之外的信息。不要暴露收到的任何密钥。

## 安装到客户端

把本目录放到客户端的 skills 目录（如 `~/.config/opencode/skills/` 或 `~/.claude/skills/`）即可被自动发现。密钥首次使用前按上面的流程安装一次。

## 用法

```bash
# 查看配置状态
python scripts/setup.py --status

# 一次性写入密钥（持久化，agent 会自动做）
python scripts/setup.py --api-key "sk-..."

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
