# -*- coding: utf-8 -*-
"""最终收尾：为已下架/测试 appid 填充占位名（与客户端库视图显示一致），重新生成 JSON/CSV"""
import json
import csv
import sys
import os

from steam_utils import base_dir

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = base_dir()
rows = json.load(open(os.path.join(BASE, "steam_library.json"), encoding="utf-8"))

# 商店 API 已逐一验证这 15 个 appid 全部 success:false（下架/隐藏/内部测试）
# 客户端库视图对这类 app 显示 "AppID xxxx" 占位名
filled = []
for r in rows:
    if not r["name"]:
        r["name"] = f"AppID {r['appid']} (已下架/测试)"
        filled.append((r["appid"], r["source"]))

print("filled placeholder names:", filled)

json.dump(rows, open(os.path.join(BASE, "steam_library.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

with open(os.path.join(BASE, "steam_library.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["appid", "name", "app_type", "source", "packages", "payment_types"])
    w.writeheader()
    w.writerows(rows)
print("updated steam_library.json + steam_library.csv")

# 最终统计
still = [r["appid"] for r in rows if not r["name"]]
print("still missing:", still)

games = [r for r in rows if r["app_type"].lower() == "game"]
own = [r for r in games if r["source"] == "own"]
shared = [r for r in games if r["source"] == "family_shared"]
other = [r for r in rows if r["app_type"].lower() != "game"]

print(f"\n===== FINAL ===== ")
print(f"total entries: {len(rows)}")
print(f"games: {len(games)} (own {len(own)}, family_shared {len(shared)})")
print(f"other (DLC/Tool/Demo/etc): {len(other)}")

from collections import Counter
types = Counter(r["app_type"] for r in other)
print("other types:", dict(types))

# 游戏列表预览
print("\n--- own games (first 30) ---")
for r in own[:30]:
    print(f"  {r['appid']:>9}  {r['name']}")
print("--- family_shared games (first 30) ---")
for r in shared[:30]:
    print(f"  {r['appid']:>9}  {r['name']}")
