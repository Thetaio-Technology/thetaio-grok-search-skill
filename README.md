# ThetaIO Grok Search Skill

![ThetaIO Grok Search](assets/hero.png)

让 AI agent 直接调用 **Grok 的实时搜索**：X（Twitter）站内帖子/用户，或公开互联网网页，返回带原始链接的可信结果。

基于 ThetaIO 网关（`https://api.thetaio.tech`）的 `POST /v1/responses` + server-side `x_search` / `web_search` 工具。

## 特性

- **X 站内搜索**：查某人最近发了什么、某话题在 X 上怎么讨论
- **公开网络搜索**：全网最新资讯、舆情、新闻
- **带信源**：自动提取 `x.com` / 网页原始链接
- **真实性校验**：读取 `usage.*_calls`，`0` 次调用会明确告警（防止模型编造）
- **工具调用可见**：`--stream --show-tools` 实时打印每一次 `x_keyword_search` / `x_user_search` / `x_semantic_search`
- **零依赖**：Python 标准库即可

## 快速开始

密钥**持久化在 skill 内部的 `scripts/config.local`**（已 gitignore，不会上传）。

```bash
# 1. 检测是否已配置
python scripts/setup.py --status

# 2. 未配置则一次性写入密钥
python scripts/setup.py --api-key "sk-..."

# 3. 直接搜索（自动读取 config.local）
python scripts/grok_search.py "latest posts from @elonmusk" --show-tools

# 公开网络搜索
python scripts/grok_search.py "latest AI news with links" --tool web

# 流式 + 展示每次工具调用
python scripts/grok_search.py "what did OpenAI ship this week" --stream --show-tools
```

**Agent 工作流**：先 `setup.py --status` 检测 → 缺 Key 时引导用户开通并用 `setup.py --api-key` 写入 → 之后每次都直接调用。配置优先级：CLI 参数 > 环境变量 `THETAIO_API_KEY` > `config.local` > 默认值。

**还没有密钥？** ThetaIO 为邀请制，可在 https://api.thetaio.tech 开号，联系微信客服 `dlin0316` 开通；已有现成的 grok 密钥（ThetaIO 或其他 OpenAI 兼容网关）也可直接交给 agent 代为配置。

> ThetaIO 的 Grok 目前为 **0.1 倍率**（按官方定价的 0.1x 计费），成本很低。

## 安装为 Skill

把本目录复制到客户端的 skills 目录：

- opencode：`~/.config/opencode/skills/thetaio-grok-search/`
- Claude Code：`~/.claude/skills/thetaio-grok-search/`

`SKILL.md` 的 `name` 必须与目录名一致（`thetaio-grok-search`）。

## 参数

| 参数 | 说明 |
|---|---|
| `query` | 自然语言查询（位置参数） |
| `--tool` | `x`（默认）/ `web` |
| `--model` | 默认 `grok-4.3`（推荐，勿用 grok-4.5） |
| `--stream` | SSE 流式输出 |
| `--show-tools` | 打印每次搜索工具调用 |
| `--json` | 输出原始 JSON |
| `--base-url` | 网关地址，默认 `https://api.thetaio.tech` |
| `--api-key` | 直接传 Key（默认读 `config.local`） |
| `--config` | 自定义 config 文件路径 |
| `--timeout` | 超时秒数，默认 180 |

## 重要提示

- 结果是否可信，看 `usage.server_side_tool_usage_details.{x,web}_search_calls` 是否 `> 0`。
- 信源在 `output[].content[].annotations[].url_citation.url`，不在 `results` 字段。
- 独立端点 `/v1/x_search`、`/v1/web_search` 仅 `grok` 平台 Key 可用（`openai` 平台返回 404）；本 skill 统一走 `/v1/responses`。
- 完整 API 文档见 [`references/grok-search-api.md`](references/grok-search-api.md)。

## License

MIT
