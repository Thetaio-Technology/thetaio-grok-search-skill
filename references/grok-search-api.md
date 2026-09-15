# ThetaIO Grok 搜索能力调用说明

> 面向需要在会话中直接调用「X 站内搜索 / 公开网络搜索」的开发者。
> 最后验证时间：2026-09-15，针对生产环境 `https://api.thetaio.tech`（0.2.4 thetaio 分支）。

---

## 0. TL;DR（先看这段）

- **Base URL**：`https://api.thetaio.tech`
- **认证**：请求头 `Authorization: Bearer <API_KEY>`
- **调用入口**：`POST /v1/responses`，在 body 的 `tools` 里声明 `x_search`（X 站内）或 `web_search`（公开互联网）
- **模型选择（关键）**：必须用 `grok-4.3` / `grok-4.20-0309-reasoning` / `grok-4.20-0309-non-reasoning`。**不要用 `grok-4.5`**，它两个工具都返回 400。
- **不要添加** `"include": ["x_search_call.action.sources"]` —— 上游会直接 400 拒绝。
- 结果中的信源在 `output[].content[].annotations[]`（`url_citation`）里，不在 `results` 字段里。

---

## 1. 两种搜索的区别

| 能力 | tool type | 搜索范围 | 返回信源 |
|---|---|---|---|
| X 站内搜索 | `x_search` | X（Twitter）站内帖子、用户 | `x.com/...` 链接 |
| 公开网络搜索 | `web_search` | 公开互联网网页 | 普通网页 URL |

两者是 xAI 官方两个独立的 server-side tool，互不包含。

---

## 2. 推荐方式：`POST /v1/responses` + `tools`

这是最通用的方式，`openai` 平台和 `grok` 平台的 group **都可以**调用。

### 2.1 请求

```bash
curl -s https://api.thetaio.tech/v1/responses \
  -H "Authorization: Bearer $THETAIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "grok-4.3",
    "input": "搜索 X 上 @xai 最近的帖子，并给出原始链接",
    "tools": [{ "type": "x_search" }],
    "store": false,
    "stream": false
  }'
```

把 `"tools": [{ "type": "x_search" }]` 换成 `"tools": [{ "type": "web_search" }]` 即为公开网络搜索。

### 2.2 参数说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `model` | 是 | 见第 4 节模型矩阵 |
| `input` | 是 | 自然语言查询/指令 |
| `tools` | 是 | `[{"type":"x_search"}]` 或 `[{"type":"web_search"}]` |
| `tool_choice` | 否 | 可省略；不建议强制设为 `"required"`（部分模型组合会 400） |
| `stream` | 否 | `false` 返回完整 JSON；`true` 返回 SSE 流 |
| `store` | 否 | 建议 `false` |

> 实测：通过 `/v1/responses` 传 `x_search` 的过滤字段（如 `allowed_x_handles`）可能被上游归一化丢弃，
> 只保留 `from_date` 等部分字段。**需要完整过滤能力请用第 3 节的独立端点。**

### 2.3 非流式响应结构（关键部分）

```jsonc
{
  "id": "05ecdef4-...",
  "model": "grok-4.3",
  "output": [
    { "type": "reasoning", "encrypted_content": "..." },
    {
      "type": "custom_tool_call",          // 上游实际执行的 X 搜索调用
      "name": "x_keyword_search",          // 或 x_user_search / x_keyword_search
      "input": "{\"query\":\"from:xai\",\"limit\":\"10\",\"mode\":\"Latest\"}",
      "status": "completed"
    },
    {
      "type": "message",
      "role": "assistant",
      "content": [
        {
          "type": "output_text",
          "text": "**Latest posts from xAI ...** [View post](https://x.com/...)",
          "annotations": [
            {
              "type": "url_citation",
              "url": "https://x.com/SpaceXAI/status/2074214064746832060",
              "title": "https://x.com/SpaceXAI/status/2074214064746832060"
            }
          ]
        }
      ]
    }
  ],
  "usage": {
    "num_server_side_tools_used": 3,
    "server_side_tool_usage_details": {
      "x_search_calls": 3,
      "web_search_calls": 0
    }
  }
}
```

**判定「是否真的搜了」**：看 `usage.server_side_tool_usage_details.x_search_calls`（或 `web_search_calls`）。
如果为 `0`，说明模型没真正调用搜索工具，返回内容可能是它编的，不要采信。

### 2.4 流式响应

`"stream": true` 时返回 SSE，最终事件为 `response.completed`，结构与非流式相同：

```
event: response.completed
data: {"type":"response.completed","response":{ ...同上... }}
```

---

## 3. 独立端点（仅 `grok` 平台 group 可用）

如果 API Key 属于 **grok 平台** 的 group，可直接调用专用的单次搜索端点，返回已被网关归一化的精简结果。
（`openai` 平台 group 调用会返回 404 `X Search API is not supported for this platform`。）

### 3.1 X 站内搜索：`POST /v1/x_search`

```bash
curl -s https://api.thetaio.tech/v1/x_search \
  -H "Authorization: Bearer $THETAIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest posts about xAI",
    "max_results": 5,
    "allowed_x_handles": ["xai"],
    "from_date": "2026-01-01",
    "to_date": "2026-09-15",
    "enable_image_understanding": true,
    "enable_video_understanding": false
  }'
```

请求字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `query` | string | 查询词（也可用 `input`） |
| `max_results` | int | 返回条数，默认 5，最大 20 |
| `allowed_x_handles` | []string | 只搜这些账号 |
| `excluded_x_handles` | []string | 排除这些账号 |
| `from_date` / `to_date` | string | 时间范围（`YYYY-MM-DD`） |
| `enable_image_understanding` | bool | 是否理解图片 |
| `enable_video_understanding` | bool | 是否理解视频 |

响应：

```json
{
  "query": "latest posts about xAI",
  "results": [
    { "url": "https://x.com/...", "title": "...", "snippet": "..." }
  ],
  "provider": "grok-native",
  "max_results": 5
}
```

### 3.2 公开网络搜索：`POST /v1/web_search`

```bash
curl -s https://api.thetaio.tech/v1/web_search \
  -H "Authorization: Bearer $THETAIO_KEY" \
  -H "Content-Type: application/json" \
  -d '{ "query": "what is xai grok", "max_results": 5 }'
```

响应结构同 `x_search`。

> 注意：该端点依赖上游真实执行搜索工具。若命中的账号/模型组合不支持（如 grok-4.5），
> 可能返回 `200` 但 `"results": null`。

---

## 4. 模型支持矩阵（实测，生产环境）

| 模型 | `x_search` | `web_search` | 备注 |
|---|---|---|---|
| `grok-4.3` | ✅ 实测 5 次调用 | ✅ 实测 3 次 | **首选** |
| `grok-4.20-0309-reasoning` | ✅ 实测 6 次 | ✅ 实测 3 次 | 可用 |
| `grok-4.20-0309-non-reasoning` | ✅ 实测 4 次 | ✅ 实测 7 次 | 可用 |
| `grok-build-0.1` | ⚠️ 可调用但 0 次搜索 | ✅ 实测 9 次 | x 搜索不生效 |
| `grok-4.5` | ❌ 上游 400 | ❌ 上游 400 | **不要用** |

> 结论：**默认用 `grok-4.3`**。

---

## 5. 结果解析示例（Python）

```python
import requests, json, re

BASE = "https://api.thetaio.tech"
KEY  = "sk-..."   # 替换为你的 Key

def search(query: str, kind: str = "x_search", model: str = "grok-4.3"):
    resp = requests.post(
        f"{BASE}/v1/responses",
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json={
            "model": model,
            "input": query,
            "tools": [{"type": kind}],
            "store": False,
            "stream": False,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()

    # 1) 是否真的执行了搜索
    detail = (data.get("usage") or {}).get("server_side_tool_usage_details") or {}
    calls = detail.get(kind + "_calls", 0)

    # 2) 信源
    citations, text = [], ""
    for item in data.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") != "output_text":
                continue
            text = part.get("text", "")
            for ann in part.get("annotations", []):
                if ann.get("type") == "url_citation":
                    citations.append(ann.get("url"))

    return {"calls": calls, "text": text, "citations": citations}

if __name__ == "__main__":
    r = search("搜索 X 上 @xai 最近的帖子", kind="x_search")
    print("搜索调用次数:", r["calls"])
    print("信源:", r["citations"][:10])
    print("回答:", r["text"][:500])
```

---

## 6. 常见问题 / 报错对照

| 现象 | 原因 | 解决 |
|---|---|---|
| `404 X Search API is not supported for this platform` | Key 属于 `openai` 平台 group，访问了独立端点 `/v1/x_search` | 改用 `/v1/responses` + `tools`，或换 grok 平台 Key |
| `400 Upstream rejected the request` | 用了 `grok-4.5`，或加了 `include:["x_search_call.action.sources"]` | 换 `grok-4.3`；删掉 `include` |
| `Model "grok-4.6" is not supported by any configured account` | 模型名不在该 group 白名单 | 用 `/v1/models` 查可用模型，选上表 4.3/4.20 |
| `200` 但 `x_search_calls=0`，链接看着像编的 | 模型没真正调工具 | 换模型为 `grok-4.3`；检查是否 `tool_choice:"required"` 导致失败 |
| `502 web_search_error` | 上游拒绝 | 参考报错 message，多为模型/参数问题 |

诊断小技巧：先用 `GET /v1/models` 确认当前 Key 有哪些模型，再用 `POST /v1/responses` 发一个最小搜索请求，看 `usage` 里的 `*_calls` 是否 > 0。

---

## 7. 计费

- 走 `/v1/responses` 的搜索按 tokens 计费（与普通对话一致）。
- 走独立端点 `/v1/x_search`、`/v1/web_search` 的按 **每次搜索 1 次** 计费，模型名分别为
  `grok-x-search` / `grok-web-search`，单价由所在 group 的 `search_price_per_1k` 控制。

---

## 8. 最小可用清单（复制即用）

```bash
KEY="sk-替换成你的Key"

# X 站内搜索
curl -s https://api.thetaio.tech/v1/responses \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"grok-4.3","input":"latest posts from @xai with links","tools":[{"type":"x_search"}],"store":false,"stream":false}'

# 公开网络搜索
curl -s https://api.thetaio.tech/v1/responses \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"grok-4.3","input":"latest AI news with source links","tools":[{"type":"web_search"}],"store":false,"stream":false}'
```
