<p align="center">
  <img src="assets/hero.webp" alt="ThetaIO Grok Search" width="100%">
</p>

# ThetaIO Grok Search Skill

让 AI agent 直接调用 Grok 的实时搜索能力，检索 **X（Twitter）站内**帖子与用户，或**公开互联网**网页，并返回原始链接作为信源。

基于 ThetaIO 网关（`https://api.thetaio.tech`）的 `POST /v1/responses` 与 server-side `x_search` / `web_search` 工具，纯 Python 标准库实现，零第三方依赖。

## 核心能力

- **X 站内搜索**：查某人（如 OpenAI 负责人 Tibo Sottiaux `@thsottiaux`）最近发了什么帖子或回复，某话题在 X 上如何讨论。
- **公开网络搜索**：检索全网最新资讯、舆情与新闻。
- **原始信源**：自动提取 `output[].content[].annotations[].url_citation.url`，交付时可验证的链接。
- **真实性校验**：读取 `usage.server_side_tool_usage_details`，`0` 次工具调用时明确告警，避免采信模型编造的内容。
- **工具调用可见**：`--stream --show-tools` 实时打印每一次 `x_keyword_search` / `x_user_search` / `x_semantic_search` 调用及其参数。
- **持久化密钥**：API Key 由 agent 管理并落盘到 `scripts/config.local`，已 gitignore，不进仓库。

## 快速开始

### 1. 环境要求

- Python 3.8+（仅标准库，无需 `pip install`）
- 可访问 `https://api.thetaio.tech` 的网络

### 2. 安装为 Skill

把本目录复制到客户端的 skills 目录即可被自动发现：

- opencode：`~/.config/opencode/skills/thetaio-grok-search/`
- Claude Code：`~/.claude/skills/thetaio-grok-search/`

也可以直接把本仓库链接发给你的 agent，让它完成克隆、放入 skills 目录与配置：

```text
帮我安装并配置这个 skill：https://github.com/Thetaio-Technology/thetaio-grok-search-skill
```

`SKILL.md` 的 `name` 必须与目录名一致（`thetaio-grok-search`）。

### 3. 配置密钥

密钥持久化在 `scripts/config.local`（已 gitignore，不会上传）。agent 会先检测，未配置时引导你开号并写入。

```bash
# 检测是否已配置
python scripts/setup.py --status

# 未配置则一次性写入密钥
python scripts/setup.py --api-key "sk-..."
```

### 4. 最小可运行示例

```bash
# X 站内搜索（默认）：查 OpenAI 负责人 Tibo Sottiaux 最近的帖子
python scripts/grok_search.py "latest posts from @thsottiaux" --show-tools

# 公开网络搜索
python scripts/grok_search.py "latest AI news with links" --tool web
```

## 配置

配置优先级：CLI 参数 > 环境变量 > `scripts/config.local` > 默认值。

| 配置项 | 来源 | 默认值 |
| --- | --- | --- |
| 网关地址 | `--base-url` / `THETAIO_BASE_URL` / `config.local` | `https://api.thetaio.tech` |
| API Key | `--api-key` / `THETAIO_API_KEY` / `THETAIO_KEY` / `config.local` | 无 |
| 模型 | `--model` / `THETAIO_MODEL` / `config.local` | `grok-4.3` |

`setup.py` 是幂等的：已有配置会跳过，不覆盖；需要修改加 `--force`。

```bash
python scripts/setup.py --status
python scripts/setup.py --api-key "sk-..."
python scripts/setup.py --api-key "sk-..." --base-url "https://other-gateway" --force
```

**还没有密钥？** ThetaIO 为邀请制，可在 https://api.thetaio.tech 开号，联系微信客服 `dlin0316` 开通；已有现成的 grok 密钥（ThetaIO 或其他 OpenAI Responses 兼容网关）也可直接交给 agent 代为配置。

> ThetaIO 的 Grok 目前为 **0.1 倍率**（按官方定价的 0.1x 计费），成本很低。

## 参数

| 参数 | 说明 |
| --- | --- |
| `query` | 自然语言查询（位置参数） |
| `--tool` | `x`（默认）/ `web` |
| `--model` | 默认 `grok-4.3`（推荐，勿用 grok-4.5） |
| `--stream` | SSE 流式输出 |
| `--show-tools` | 打印每次搜索工具调用 |
| `--json` | 输出原始 JSON |
| `--base-url` | 网关地址 |
| `--api-key` | 直接传 Key |
| `--config` | 自定义 config 文件路径 |
| `--timeout` | 超时秒数，默认 180 |

## 目录结构

```text
thetaio-grok-search/
  SKILL.md                        # 技能主文档，agent 读取入口
  README.md
  LICENSE
  .gitignore
  assets/
    hero.webp                     # README 首屏 banner
    raw/                          # 生图原图（gitignore）
  references/
    grok-search-api.md            # 完整 API 规范、报错对照、模型矩阵
  scripts/
    setup.py                      # 一次性配置密钥（幂等）
    grok_search.py                # 搜索调用脚本
    config.local                  # 持久化密钥（gitignore）
```

## 安全说明

- 本仓库**不含任何密钥**。
- 密钥写入 `scripts/config.local`，该文件已被 `.gitignore` 忽略；请勿提交。
- `setup.py --status` 与脚本回显均对密钥做掩码处理（如 `sk-6ef...c841`）。
- 不要把密钥贴进公开渠道；已提交过的密钥应视为泄露，去后台吊销并换新。

## 重要提示

- 结果是否可信，看 `usage.server_side_tool_usage_details.{x,web}_search_calls` 是否 `> 0`。
- 信源在 `output[].content[].annotations[].url_citation.url`，不在 `results` 字段。
- 独立端点 `/v1/x_search`、`/v1/web_search` 仅 `grok` 平台 Key 可用（`openai` 平台返回 404）；本 skill 统一走 `/v1/responses`。
- 完整 API 规范、报错对照表与模型支持矩阵见 [`references/grok-search-api.md`](references/grok-search-api.md)。

## License

MIT
