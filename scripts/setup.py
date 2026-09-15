#!/usr/bin/env python3
"""Grok 搜索 skill 配置脚本 —— 首次安装，把 base_url / api_key 写入 scripts/config.local。

只需安装一次。之后 grok_search.py 会自动读取该文件，无需重复安装。

用法：

    # 交互式（终端手动运行）
    python scripts/setup.py

    # 非交互式（交给 agent 调用）
    python scripts/setup.py --api-key "sk-..."

    # 覆盖已有配置
    python scripts/setup.py --force

    # 查看当前配置状态（不修改）
    python scripts/setup.py --status

config.local 已被 .gitignore 忽略，不会被提交。
"""

from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.local"
CONFIG_CANDIDATES = (SCRIPT_DIR / "config.local", SCRIPT_DIR / "config")
DEFAULT_BASE_URL = "https://api.thetaio.tech"
DEFAULT_MODEL = "grok-4.3"


def load_key_value_config(path: pathlib.Path) -> dict:
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


def find_existing_config():
    for candidate in CONFIG_CANDIDATES:
        if candidate.exists():
            config = load_key_value_config(candidate)
            if config.get("api_key"):
                return candidate, config
    return None


def mask(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 12:
        return secret[:4] + "***"
    return f"{secret[:6]}...{secret[-4:]}"


def write_config(base_url: str, api_key: str, model: str) -> pathlib.Path:
    content = (
        "# 由 scripts/setup.py 生成，请勿提交到版本库。\n"
        "# 如需重新配置，运行 python scripts/setup.py --force\n"
        f"base_url: {base_url}\n"
        f"api_key: {api_key}\n"
        f"model: {model}\n"
    )
    CONFIG_PATH.write_text(content, encoding="utf-8")
    try:
        CONFIG_PATH.chmod(0o600)
    except OSError:
        pass
    return CONFIG_PATH


def parse_args():
    parser = argparse.ArgumentParser(description="ThetaIO Grok 搜索 skill 配置脚本")
    parser.add_argument("--base-url", help=f"网关地址，默认 {DEFAULT_BASE_URL}")
    parser.add_argument("--api-key", help="ThetaIO API Key")
    parser.add_argument("--model", help=f"默认模型，默认 {DEFAULT_MODEL}")
    parser.add_argument("--force", action="store_true", help="已有配置时强制覆盖")
    parser.add_argument("--status", action="store_true", help="仅打印当前配置状态后退出")
    return parser.parse_args()


def print_status():
    existing = find_existing_config()
    if not existing:
        print("未配置：没有找到可用的 api_key。")
        print('运行 python scripts/setup.py --api-key "sk-..." 写入。')
        print("还没有密钥？ThetaIO 为邀请制，可在 https://api.thetaio.tech 开号，")
        print("联系微信客服 dlin0316 开通（ThetaIO 的 Grok 为 0.1 倍率）；")
        print("已有其他 grok 密钥也可直接交给 agent 配置。")
        return 1
    path, config = existing
    print(f"已配置: {path}")
    print(f"base_url: {config.get('base_url', DEFAULT_BASE_URL)}")
    print(f"api_key:  {mask(config.get('api_key', ''))}")
    print(f"model:    {config.get('model', DEFAULT_MODEL)}")
    return 0


def prompt_value(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default:
            return default
        print("该值不能为空，请重新输入。")


def main() -> int:
    args = parse_args()

    if args.status:
        return print_status()

    if not args.force:
        existing = find_existing_config()
        if existing:
            path, config = existing
            print(f"已配置，跳过安装: {path}")
            print(f"base_url: {config.get('base_url', DEFAULT_BASE_URL)}")
            print(f"api_key:  {mask(config.get('api_key', ''))}")
            print(f"model:    {config.get('model', DEFAULT_MODEL)}")
            print("如需修改，运行: python scripts/setup.py --force")
            return 0

    base_url = args.base_url
    api_key = args.api_key
    model = args.model

    fully_interactive = not base_url and not api_key

    if fully_interactive:
        print("首次安装：请填入 ThetaIO 配置（直接回车使用默认值）。")
        base_url = prompt_value("ThetaIO API 地址 (base_url)", DEFAULT_BASE_URL)

    if not api_key:
        api_key = prompt_value("ThetaIO API Key")

    if not model and fully_interactive:
        model = prompt_value("默认模型", DEFAULT_MODEL)

    base_url = (base_url or DEFAULT_BASE_URL).strip().rstrip("/")
    model = (model or DEFAULT_MODEL).strip()
    api_key = (api_key or "").strip()

    if not api_key:
        print("错误: api_key 不能为空", file=sys.stderr)
        return 1

    path = write_config(base_url, api_key, model)
    print(f"配置已写入: {path}")
    print(f"base_url: {base_url}")
    print(f"api_key:  {mask(api_key)}")
    print(f"model:    {model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
