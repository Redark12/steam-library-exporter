# -*- coding: utf-8 -*-
"""解析新版 appinfo.vdf (0x07564429) 提取 appid -> name/type
VDF 范围 = [pos+68, pos+8+size)，name/type 用正则扫描（对 extended 特殊编码免疫）
"""
import struct
import re
import json
import os
import sys

from steam_utils import base_dir, find_steam_dir

STEAM_DIR = find_steam_dir()
if not STEAM_DIR:
    print("ERROR: 未找到 Steam 安装目录")
    sys.exit(1)
PATH = os.path.join(STEAM_DIR, "appcache", "appinfo.vdf")
OUT = os.path.join(base_dir(), "appinfo_map.json")

with open(PATH, "rb") as f:
    data = f.read()
LEN = len(data)

PAT_NAME = re.compile(rb"\x01\x04\x00\x00\x00([^\x00]{1,200})\x00")
PAT_TYPE = re.compile(rb"\x01\x05\x00\x00\x00([^\x00]{1,60})\x00")

def valid_record(pos):
    if pos + 68 > LEN:
        return False
    appid = struct.unpack_from("<I", data, pos)[0]
    size = struct.unpack_from("<I", data, pos + 4)[0]
    return 0 < appid < 0x7FFFFFFF and 0 < size < 0x100000 and pos + 8 + size <= LEN

apps = {}
pos = 16
nrec = 0
while valid_record(pos):
    appid = struct.unpack_from("<I", data, pos)[0]
    size = struct.unpack_from("<I", data, pos + 4)[0]
    vdf_start = pos + 68
    vdf_end = pos + 8 + size
    seg = data[vdf_start:vdf_end]

    name = ""
    atype = ""
    m = PAT_NAME.search(seg)
    if m:
        name = m.group(1).decode("utf-8", "replace")
    m = PAT_TYPE.search(seg)
    if m:
        atype = m.group(1).decode("utf-8", "replace")

    apps[str(appid)] = {"name": name, "type": atype}
    if nrec < 10:
        print(f"appid={appid} size={size} name={name!r} type={atype!r}")
    nrec += 1
    nxt = vdf_end
    if not valid_record(nxt):
        # 自愈：向后扫描同步
        nxt += 4
        while nxt + 68 <= LEN and not valid_record(nxt):
            nxt += 4
    pos = nxt

named = sum(1 for a in apps.values() if a["name"])
print(f"records: {nrec}, with name: {named}, with type: {sum(1 for a in apps.values() if a['type'])}")

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(apps, f, ensure_ascii=False)
print("saved", OUT)
