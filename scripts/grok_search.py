#!/usr/bin/env python3
"""Grok 搜索：通过 ThetaIO 网关调用 X 站内搜索 / 公开网络搜索。

仅依赖 Python 标准库。用法见 --help，或 SKILL.md。
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_BASE = os.environ.get("THETAIO_BASE_URL", "https://api.thetaio.tech")
DEFAULT_MODEL = "grok-4.3"

TOOL_ALIASES = {
    "x": "x_search",
    "x_search": "x_search",
    "web": "web_search",
    "web_search": "web_search",
}


def resolve_key(cli_key):
    key = cli_key or os.environ.get("THETAIO_API_KEY") or os.environ.get("THETAIO_KEY")
    if not key:
        sys.exit(
            "缺少 API Key：请设置环境变量 THETAIO_API_KEY，或用 --api-key 传入。"
        )
    return key


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        prog="grok_search",
        description="通过 ThetaIO 网关调用 Grok 的 X 站内搜索 / 公开网络搜索。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  grok_search.py \"latest posts from @elonmusk\"\n"
            "  grok_search.py \"latest AI news\" --tool web\n"
            "  grok_search.py \"what did OpenAI ship this week\" --stream --show-tools\n"
            "  grok_search.py \"posts from @thsottiaux\" --json\n"
        ),
    )
    p.add_argument("query", help="自然语言查询或搜索指令")
    p.add_argument(
        "--tool",
        default="x",
        help="搜索类型：x / x_search（X 站内，默认）或 web / web_search（公开网络）",
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"模型，默认 {DEFAULT_MODEL}")
    p.add_argument("--base-url", default=DEFAULT_BASE, help="网关地址")
    p.add_argument("--api-key", default=None, help="API Key（默认取 THETAIO_API_KEY）")
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

    key = resolve_key(args.api_key)
    body = build_body(args, kind, args.stream)
    resp = request(args.base_url, key, body, args.timeout)

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
