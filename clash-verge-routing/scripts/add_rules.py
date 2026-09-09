#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_rules.py — 向 Clash Verge Rev 的订阅规则扩展文件添加「域名 -> 直连/代理」规则（幂等）

用法示例:
  python add_rules.py --direct aps.org nature.com arxiv.org
  python add_rules.py --proxy youtube.com netflix.com --proxy-policy PROXY
  python add_rules.py --direct aps.org --proxy openai.com          # 同一批混合
  python add_rules.py --list                                       # 查看当前规则
  python add_rules.py --rules-file <某rules扩展文件> --direct x.com  # 指定文件
  python add_rules.py --dry-run --direct aps.org                   # 仅预览不写入

说明:
  - 默认自动定位当前订阅绑定的 rules 扩展文件（读 profiles.yaml 的 current + option.rules）
  - 修改前自动备份（同名 .bak-时间戳）
  - 已存在的规则不会重复添加
  - 依赖 PyYAML；缺失时先 `python -m pip install pyyaml`
"""
import argparse
import json
import os
import shutil
import sys
import time

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML，请先执行: python -m pip install pyyaml", file=sys.stderr)
    sys.exit(1)

# Clash Verge Rev 配置目录候选（%APPDATA% 下）
VERGE_DIR_CANDIDATES = [
    os.path.join(os.environ.get("APPDATA", ""), "io.github.clash-verge-rev.clash-verge-rev"),
    os.path.join(os.environ.get("APPDATA", ""), "clash-verge"),
]


def find_verge_dir():
    for d in VERGE_DIR_CANDIDATES:
        if os.path.isdir(os.path.join(d, "profiles")):
            return d
    return None


def find_rules_file(verge_dir):
    """按 profiles.yaml 的 current + option.rules 定位当前订阅绑定的 rules 扩展文件"""
    pprof = os.path.join(verge_dir, "profiles.yaml")
    if not os.path.isfile(pprof):
        return None
    with open(pprof, "r", encoding="utf-8") as f:
        text = f.read()
    try:
        data = yaml.safe_load(text) or {}
    except Exception:
        return None
    current = data.get("current")
    items = data.get("items") or []
    cur_item = None
    for it in items:
        if it.get("uid") == current:
            cur_item = it
            break
    rules_uid = None
    if cur_item:
        opt = cur_item.get("option") or {}
        rules_uid = opt.get("rules")
    # 回退：任选一个 type=rules 的扩展文件
    if not rules_uid:
        for it in items:
            if it.get("type") == "rules":
                rules_uid = it.get("uid")
                break
    if not rules_uid:
        return None
    for it in items:
        if it.get("uid") == rules_uid:
            return os.path.join(verge_dir, "profiles", it.get("file"))
    return None


def load_rules(path):
    if not os.path.isfile(path):
        return {"prepend": [], "append": [], "delete": []}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {
        "prepend": [str(x) for x in (data.get("prepend") or [])],
        "append": [str(x) for x in (data.get("append") or [])],
        "delete": [str(x) for x in (data.get("delete") or [])],
    }


def save_rules(path, data, backup=True):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if backup and os.path.isfile(path):
        bak = f"{path}.bak-{time.strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(path, bak)
    header = "# Clash Verge 规则扩展文件 (由 clash-verge-routing/add_rules.py 维护)\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def build_rules(direct, proxy, proxy_policy):
    rules = []
    for d in direct or []:
        d = d.strip().lower().strip(".")
        if d:
            rules.append(f"DOMAIN-SUFFIX,{d},DIRECT")
    for d in proxy or []:
        d = d.strip().lower().strip(".")
        if d:
            rules.append(f"DOMAIN-SUFFIX,{d},{proxy_policy or 'PROXY'}")
    return rules


def print_rules(verge_dir, path, rules):
    print(f"Clash Verge 目录 : {verge_dir}")
    print(f"规则扩展文件     : {path}")
    print(f"prepend 规则数   : {len(rules['prepend'])}")
    print(f"append  规则数   : {len(rules['append'])}")
    print("--- prepend ---")
    for r in rules["prepend"]:
        print("  " + r)


def main():
    ap = argparse.ArgumentParser(description="向 Clash Verge Rev 规则扩展文件添加直连/代理规则")
    ap.add_argument("--direct", nargs="*", default=[], help="要直连(DIRECT)的域名列表，如 aps.org nature.com")
    ap.add_argument("--proxy", nargs="*", default=[], help="要走代理的域名列表")
    ap.add_argument("--proxy-policy", default="PROXY", help="代理规则使用的策略名(默认 PROXY；可写具体组名)")
    ap.add_argument("--rules-file", default=None, help="指定 rules 扩展文件路径(跳过自动定位)")
    ap.add_argument("--dry-run", action="store_true", help="只预览，不写入")
    ap.add_argument("--list", action="store_true", help="查看当前规则")
    args = ap.parse_args()

    verge_dir = find_verge_dir()
    if not verge_dir:
        print("[错误] 未找到 Clash Verge 配置目录(profiles)。", file=sys.stderr)
        sys.exit(1)
    path = args.rules_file or find_rules_file(verge_dir)
    if not path:
        print("[错误] 未定位到订阅绑定的 rules 扩展文件。", file=sys.stderr)
        print("      请先在 Clash Verge 界面: 订阅页 -> 当前订阅 -> 编辑 -> 添加「规则扩展」(Rules)", file=sys.stderr)
        sys.exit(1)

    rules = load_rules(path)

    if args.list:
        print_rules(verge_dir, path, rules)
        return

    new_rules = build_rules(args.direct, args.proxy, args.proxy_policy)
    if not new_rules:
        print("[提示] 没有需要添加的规则(--direct/--proxy 均为空)")
        return

    existing = set(rules["prepend"])
    added = [r for r in new_rules if r not in existing]
    dup = [r for r in new_rules if r in existing]
    print(f"准备添加 {len(added)} 条规则 (已存在跳过 {len(dup)} 条)")
    for r in added:
        print("  + " + r)
    if dup:
        print("  已存在: " + ", ".join(dup))

    if args.dry_run:
        print("[dry-run] 未写入任何文件")
        return
    if not added:
        print("[提示] 无新增规则，文件未改动")
        return

    rules["prepend"] = added + rules["prepend"]
    save_rules(path, rules)
    print(f"[完成] 已写入 {path}")
    print("[提示] 需要重新加载配置才会生效：Clash Verge 界面 -> 订阅页 -> 当前订阅 -> 重新激活（或右下角重启内核）")


if __name__ == "__main__":
    main()
