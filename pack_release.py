# -*- coding: utf-8 -*-
"""打包分享版：把源码和启动脚本打成 zip（不含个人游戏库数据）"""
import os
import shutil
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = os.path.dirname(os.path.abspath(__file__))

# 分享清单（只含代码与说明，不含任何个人数据文件）
FILES = [
    "main.py",
    "steam_utils.py",
    "parse_appinfo.py",
    "build_library.py",
    "finalize_names.py",
    "run.bat",
    "requirements.txt",
    "README.md",
]

# 个人数据文件（绝不打包）
PRIVATE = ["steam_library.json", "steam_library.csv",
           "appinfo_map.json", "pack_release.py", "release"]

RELEASE_DIR = os.path.join(BASE, "release")
PKG_NAME = "steam-library-exporter"
PKG_DIR = os.path.join(RELEASE_DIR, PKG_NAME)
ZIP_PATH = os.path.join(RELEASE_DIR, PKG_NAME + ".zip")

if os.path.exists(RELEASE_DIR):
    shutil.rmtree(RELEASE_DIR)
os.makedirs(PKG_DIR)

missing = []
for name in FILES:
    src = os.path.join(BASE, name)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(PKG_DIR, name))
    else:
        missing.append(name)

if missing:
    print("ERROR: 缺少文件:", missing)
    sys.exit(1)

with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for name in FILES:
        z.write(os.path.join(PKG_DIR, name), os.path.join(PKG_NAME, name))

# 校验：列出包内文件，确认无隐私文件
with zipfile.ZipFile(ZIP_PATH) as z:
    names = z.namelist()
print("已打包:", ZIP_PATH)
print("包内文件:", [os.path.basename(n) for n in names])
leaked = [n for n in names if os.path.basename(n) in PRIVATE]
print("隐私文件泄露检查:", "发现泄露!!" if leaked else "通过（无个人数据）")
