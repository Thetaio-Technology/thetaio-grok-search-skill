#!/usr/bin/env python3
"""Grok 搜索：通过 ThetaIO 网关调用 X 站内搜索 / 公开网络搜索。

仅依赖 Python 标准库。用法见 --help，或 SKILL.md。
"""

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_CANDIDATES = (SCRIPT_DIR / "config.local", SCRIPT_DIR / "config")

DEFAULT_BASE = "https://api.thetaio.tech"
DEFAULT_MODEL = "grok-4.3"
NO_KEY_MARKER = "[NO_API_KEY]"

ENV_BASE_KEYS = ("THETAIO_BASE_URL",)
ENV_KEY_KEYS = ("THETAIO_API_KEY", "THETAIO_KEY")
ENV_MODEL_KEYS = ("THETAIO_MODEL",)

TOOL_ALIASES = {
    "x": "x_search",
    "x_search": "x_search",
    "web": "web_search",
    "web_search": "web_search",
}


def load_key_value_config(path):
    if not path.exists():
        return {}
    parsed = {}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.split("#", 1)[0].strip()
    return parsed


def find_config_path(explicit=None):
    if explicit:
        p = pathlib.Path(explicit).expanduser()
        if not p.exists():
            raise RuntimeError(f"config 文件不存在: {p}")
        return p
    for candidate in CONFIG_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def first_env(keys):
    for k in keys:
        v = os.environ.get(k)
        if v:
            return v
    return None


def resolve_config(cli_key, cli_base, cli_model, config_path=None):
    """按优先级返回 (base_url, api_key, model)：
    CLI 参数 > 环境变量 > scripts/config.local > 默认值。"""
    path = find_config_path(config_path)
    file_cfg = load_key_value_config(path) if path else {}

    base_url = (
        cli_base or first_env(ENV_BASE_KEYS) or file_cfg.get("base_url") or DEFAULT_BASE
    ).rstrip("/")
    api_key = cli_key or first_env(ENV_KEY_KEYS) or file_cfg.get("api_key")
    model = cli_model or first_env(ENV_MODEL_KEYS) or file_cfg.get("model") or DEFAULT_MODEL

    if not api_key:
        sys.exit(
            f"{NO_KEY_MARKER} 未找到 ThetaIO API Key。\n"
            "请让 agent 运行以下命令完成一次性配置（持久化到 scripts/config.local）：\n"
            f'  python "{SCRIPT_DIR / "setup.py"}" --api-key "sk-..."\n'
            "还没有密钥？ThetaIO 为邀请制，可在 https://api.thetaio.tech 开号，\n"
            "联系微信客服 dlin0316 开通（ThetaIO 的 Grok 为 0.1 倍率）；\n"
            "已有其他 grok 密钥也可直接交给 agent 配置。\n"
            "或设置环境变量 THETAIO_API_KEY，或用 --api-key 传入。"
        )
    return base_url, api_key, model


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="grok_search",
        description="通过 ThetaIO 网关调用 Grok 的 X 站内搜索 / 公开网络搜索。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  grok_search.py \"latest posts from @thsottiaux\"   # OpenAI 负责人 Tibo\n"
            "  grok_search.py \"latest AI news\" --tool web\n"
            "  grok_search.py \"what did OpenAI ship this week\" --stream --show-tools\n"
            "  grok_search.py \"posts from @elonmusk\" --json\n"
        ),
    )
    p.add_argument("query", help="自然语言查询或搜索指令")
    p.add_argument(
        "--tool",
        default="x",
        help="搜索类型：x / x_search（X 站内，默认）或 web / web_search（公开网络）",
    )
    p.add_argument("--model", default=None, help=f"模型，默认 {DEFAULT_MODEL}")
    p.add_argument("--base-url", default=None, help="网关地址，默认 https://api.thetaio.tech")
    p.add_argument("--api-key", default=None, help="API Key（默认读取 scripts/config.local）")
    p.add_argument("--config", default=None, help="可选的 config.local 路径")
    p.add_argument("--stream", action="store_true", help="使用 SSE 流式输出")
    p.add_argument("--show-tools", action="store_true", help="打印每次搜索工具调用（推荐配合 --stream）")
    p.add_argument("--json", action="store_true", help="输出原始 JSON（非流式）")
    p.add_argument("--timeout", type=int, default=180, help="超时秒数，默认 180")
    return p.parse_args(argv)


def build_body(args, kind, stream):
    return {
        "model": args.model,
        "input": args.query,
        "tools": [{"type": kind}],
        "store": False,
        "stream": stream,
    }


def request(base_url, key, body, timeout):
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if body.get("stream") else "application/json",
        },
        method="POST",
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")
        sys.exit(f"HTTP {e.code} 调用失败：{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误：{e.reason}")


def extract_result(data, kind):
    detail = ((data.get("usage") or {}).get("server_side_tool_usage_details")) or {}
    calls = detail.get(kind + "_calls", 0)

    text, citations, tool_calls = "", [], []
    for item in data.get("output", []):
        itype = item.get("type")
        if itype == "custom_tool_call":
            tool_calls.append(
                {
                    "name": item.get("name"),
                    "input": item.get("input"),
                    "status": item.get("status"),
                }
            )
        elif itype == "message":
            for part in item.get("content", []):
                if part.get("type") != "output_text":
                    continue
                text = part.get("text", "")
                for ann in part.get("annotations", []):
                    if ann.get("type") == "url_citation" and ann.get("url"):
                        citations.append(ann["url"])

    seen, uniq = set(), []
    for c in citations:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return {"calls": calls, "text": text, "citations": uniq, "tool_calls": tool_calls}


def run_stream(args, resp, kind):
    calls, citations, text_parts = 0, [], []
    seen = set()
    cur_event = ""
    for raw in resp:
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        if line.startswith("event:"):
            cur_event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break

        if cur_event == "response.output_item.added":
            try:
                item = json.loads(data).get("item", {})
            except json.JSONDecodeError:
                item = {}
            if item.get("type") == "custom_tool_call" and args.show_tools:
                print(f"[tool] {item.get('name') or 'x_search'} 开始调用", file=sys.stderr)
        elif cur_event == "response.custom_tool_call_input.done":
            calls += 1
            if args.show_tools:
                try:
                    payload = json.loads(data)
                    print(
                        f"[tool] {payload.get('name', 'x_search')} "
                        f"input={payload.get('input', '')}",
                        file=sys.stderr,
                    )
                except json.JSONDecodeError:
                    pass
        elif cur_event == "response.output_text.delta":
            try:
                delta = json.loads(data).get("delta", "")
            except json.JSONDecodeError:
                delta = ""
            text_parts.append(delta)
            if not args.json:
                sys.stdout.write(delta)
                sys.stdout.flush()
        elif cur_event == "response.output_text.annotation.added":
            try:
                ann = json.loads(data).get("annotation", {})
            except json.JSONDecodeError:
                ann = {}
            url = ann.get("url")
            if url and url not in seen:
                seen.add(url)
                citations.append(url)

    if not args.json and text_parts:
        sys.stdout.write("\n")
    return {"calls": calls, "text": "".join(text_parts), "citations": citations,
            "tool_calls": []}


def main(argv=None):
    args = parse_args(argv)
    kind = TOOL_ALIASES.get(args.tool.lower())
    if not kind:
        sys.exit(f"未知 --tool：{args.tool}（可选 x / x_search / web / web_search）")

    base_url, key, model = resolve_config(
        args.api_key, args.base_url, args.model, args.config
    )
    args.model = model
    body = build_body(args, kind, args.stream)
    resp = request(base_url, key, body, args.timeout)

    if args.stream:
        result = run_stream(args, resp, kind)
    else:
        data = json.loads(resp.read().decode("utf-8"))
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
        result = extract_result(data, kind)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print("\n" + "=" * 60)
    print(f"搜索调用次数: {result['calls']}")
    if result["calls"] == 0:
        print("⚠️  模型没有真正调用搜索工具，结果可能是编造的，请勿采信。")
    if result["citations"]:
        print("信源:")
        for c in result["citations"]:
            print(f"  - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
