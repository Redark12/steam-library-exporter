# -*- coding: utf-8 -*-
"""合并许可证数据 + appinfo 名称映射，输出完整游戏库列表"""
import re
import json
import csv
import sys
import os
from collections import Counter

from steam_utils import base_dir, find_steam_dir

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STEAM_DIR = find_steam_dir()
if not STEAM_DIR:
    print("ERROR: 未找到 Steam 安装目录")
    sys.exit(1)
LOG_PATH = os.path.join(STEAM_DIR, "logs", "console_log.txt")
LOG_PREV_PATH = os.path.join(STEAM_DIR, "logs", "console_log.previous.txt")
APPMAP_PATH = os.path.join(base_dir(), "appinfo_map.json")
OUT_JSON = os.path.join(base_dir(), "steam_library.json")
OUT_CSV = os.path.join(base_dir(), "steam_library.csv")

# ---------- 1. 解析许可证 ----------
# 日志写满约 512KB 会轮转：console_log.txt -> console_log.previous.txt，
# 单次 licenses_print 输出可能横跨两个文件，需拼接
text = ""
for p in (LOG_PREV_PATH, LOG_PATH):
    try:
        text += open(p, encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        pass

# 日志会累积，只取最后一次 licenses_print 输出（按时间戳定位）
starts = [m.start() for m in re.finditer(r"License packageID \d+:", text)]
if not starts:
    print("ERROR: console_log.txt 中未找到 licenses_print 输出")
    print("请先打开 Steam 控制台（steam://open/console）并执行 licenses_print")
    sys.exit(1)
start_idx = 0
m_ts = re.search(r"\[([\d\- :]+)\]", text[starts[-1]:starts[-1] + 80])
if m_ts:
    last_ts = m_ts.group(1)
    for i in range(len(starts) - 1, -1, -1):
        m = re.search(r"\[([\d\- :]+)\]", text[starts[i]:starts[i] + 80])
        if m and m.group(1) != last_ts:
            start_idx = i + 1
            break
text = text[starts[start_idx]:]

m_end = text.rfind("in total)")
if m_end != -1:
    line_end = text.find("\n", m_end)
    if line_end != -1:
        text = text[:line_end]

blocks = re.split(r"License packageID (\d+):", text)

licenses = []
for i in range(1, len(blocks), 2):
    pkg = blocks[i]
    body = blocks[i + 1]
    # Purchased 类型：行尾 `"CN", XXX` 后的 XXX（可能多词，如 Family Group）
    m = re.search(r"- Purchased\s*:(.*)$", body, re.M)
    ptype = "Unknown"
    if m:
        line = m.group(1)
        mm = re.search(r"\"(\w*)\"\s*,\s*(.+?)\s*$", line)
        if mm:
            ptype = mm.group(2).strip()
        elif "Free" in line:
            ptype = "Free"
    # Apps 列表：`- Apps :` 之后到 `(N in total)` 之间的数字
    ma = re.search(r"- Apps\s*:\s*(.*?)\((\d+) in total\)", body, re.S)
    appids = [int(x) for x in re.findall(r"(\d+)", ma.group(1))] if ma else []
    licenses.append({"package": pkg, "type": ptype, "apps": appids})

print("licenses:", len(licenses))
print("payment types:", dict(Counter(l["type"] for l in licenses)))

# ---------- 2. 归属分类 ----------
own_apps = {}    # appid -> {packages, types}
shared_apps = {}
for lic in licenses:
    is_family = "Family Group" in lic["type"]
    for aid in lic["apps"]:
        bucket = shared_apps if is_family else own_apps
        e = bucket.setdefault(aid, {"packages": [], "types": []})
        e["packages"].append(lic["package"])
        if lic["type"] not in e["types"]:
            e["types"].append(lic["type"])

# 自有优先：同一 appid 若既有自有又有共享许可证，归为自有
for aid in list(shared_apps.keys()):
    if aid in own_apps:
        for p in shared_apps[aid]["packages"]:
            own_apps[aid]["packages"].append(p)
        own_apps[aid]["types"].append("Family Group")
        del shared_apps[aid]

print(f"own apps: {len(own_apps)}, family shared apps: {len(shared_apps)}")

# ---------- 3. 名称/类型映射 ----------
appmap = json.load(open(APPMAP_PATH, encoding="utf-8"))
missing = []

def lookup(aid):
    e = appmap.get(str(aid))
    if e and e.get("name"):
        return e["name"], e.get("type", "")
    missing.append(aid)
    return "", ""

# ---------- 4. 组装输出 ----------
rows = []
for aid, info in own_apps.items():
    name, atype = lookup(aid)
    rows.append({
        "appid": aid,
        "name": name,
        "app_type": atype,
        "source": "own",
        "packages": ",".join(info["packages"]),
        "payment_types": ",".join(info["types"]),
    })
for aid, info in shared_apps.items():
    name, atype = lookup(aid)
    rows.append({
        "appid": aid,
        "name": name,
        "app_type": atype,
        "source": "family_shared",
        "packages": ",".join(info["packages"]),
        "payment_types": ",".join(info["types"]),
    })

rows.sort(key=lambda r: (r["source"], r["name"].lower()))

games = [r for r in rows if r["app_type"].lower() == "game"]
print(f"total entries: {len(rows)}, games: {len(games)}, missing names: {len(set(missing))}")

json.dump(rows, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["appid", "name", "app_type", "source", "packages", "payment_types"])
    w.writeheader()
    w.writerows(rows)
print("saved", OUT_JSON, "and", OUT_CSV)

# ---------- 5. 摘要 ----------
own_games = [r for r in rows if r["source"] == "own" and r["app_type"].lower() == "game"]
shared_games = [r for r in rows if r["source"] == "family_shared" and r["app_type"].lower() == "game"]
print(f"\n=== SUMMARY ===")
print(f"own games: {len(own_games)}")
print(f"family shared games: {len(shared_games)}")
print(f"other (dlc/tool/demo/music): {len(rows) - len(games)}")
print("\nown games:")
for r in own_games:
    print(f"  {r['appid']:>8}  {r['name']}")
print("\nfamily shared games:")
for r in shared_games:
    print(f"  {r['appid']:>8}  {r['name']}")
