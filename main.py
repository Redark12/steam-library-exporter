# -*- coding: utf-8 -*-
"""一键刷新 Steam 游戏库数据（入口脚本）
流程：打开控制台 -> 自动输入 licenses_print -> 验证日志更新 -> parse -> build -> finalize
自动输入失败时降级为提示用户手动输入，随后自动继续流水线。
"""
import subprocess
import time
import sys
import os
import re

from steam_utils import base_dir, find_steam_dir

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = base_dir()
PY = sys.executable
STEAM_DIR = find_steam_dir()
if not STEAM_DIR:
    print("ERROR: 未找到 Steam 安装目录（注册表无记录且默认路径不存在）")
    sys.exit(1)
LOG = os.path.join(STEAM_DIR, "logs", "console_log.txt")
LOG_PREV = os.path.join(STEAM_DIR, "logs", "console_log.previous.txt")
STEAM_EXE = os.path.join(STEAM_DIR, "steam.exe")


def read_logs():
    text = ""
    for p in (LOG_PREV, LOG):
        try:
            text += open(p, encoding="utf-8", errors="replace").read()
        except FileNotFoundError:
            pass
    return text


def last_output_ts(text):
    """日志中最后一次 licenses_print 输出的时间戳"""
    starts = [m.start() for m in re.finditer(r"License packageID \d+:", text)]
    if not starts:
        return ""
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]", text[starts[-1]:starts[-1] + 80])
    return m.group(1) if m else ""


def steam_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq steam.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=10)
        return "steam.exe" in out.stdout
    except Exception:
        return False


def open_console():
    """触发 steam://open/console 打开控制台 tab"""
    subprocess.Popen(["cmd", "/c", "start", "", "steam://open/console"],
                     shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find_steam_window():
    """找到可见的 Steam 主窗口（UIA）"""
    try:
        from pywinauto import Desktop
        for w in Desktop(backend="uia").windows():
            try:
                if w.window_text() == "Steam" and w.is_visible():
                    return w
            except Exception:
                continue
    except Exception:
        pass
    return None


def wait_steam_window(timeout=120):
    """等待 Steam 主窗口可见"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if find_steam_window():
            return True
        time.sleep(3)
    return False


def try_auto_input(attempts=6, interval=4):
    """尝试用 UIA 找到控制台输入框并输入 licenses_print
    带重试：控制台 tab 首次打开时 CEF 渲染/UIA 树构建需要时间"""
    for i in range(attempts):
        try:
            from pywinauto import Desktop
            d = Desktop(backend="uia")
            for w in d.windows():
                try:
                    if w.window_text() != "Steam" or not w.is_visible():
                        continue
                except Exception:
                    continue
                try:
                    edits = [e for e in w.descendants(control_type="Edit")]
                except Exception:
                    edits = []
                if not edits:
                    continue
                # 控制台输入框在窗口底部：选 bounding_rectangle 底边最大的 Edit
                def bottom(e):
                    try:
                        return e.bounding_rectangle().bottom
                    except Exception:
                        return -1
                edits.sort(key=bottom, reverse=True)
                edit = edits[0]
                edit.set_focus()
                time.sleep(0.5)
                edit.type_keys("licenses_print{ENTER}", with_spaces=True)
                return True
        except Exception as e:
            print(f"  [auto input] attempt {i + 1}/{attempts} failed: {e}")
        time.sleep(interval)
    return False


def wait_log_update(ts_before, timeout=40):
    """等待日志中出现比 ts_before 更新的 licenses_print 输出"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        ts_after = last_output_ts(read_logs())
        if ts_after and ts_after > ts_before:
            return ts_after
        time.sleep(3)
    return ""


def run_script(step, path):
    print(f"\n[{step}] {os.path.basename(path)} ...")
    r = subprocess.run([PY, path], capture_output=False)
    if r.returncode != 0:
        print(f"  !! {step} failed (exit {r.returncode})")
        return False
    return True


def main():
    print("=== Steam 游戏库一键刷新 ===\n")

    # 1. 确保 Steam 在运行
    if not steam_running():
        print("[1/5] Steam 未运行，正在启动...")
        subprocess.Popen([STEAM_EXE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not wait_steam_window(120):
            print("!! Steam 窗口 2 分钟内未出现，请手动启动后重跑本脚本")
            sys.exit(1)
        print("    Steam 已启动，等待界面就绪 ...")
        time.sleep(8)
    else:
        print("[1/5] Steam 正在运行")
        if not wait_steam_window(30):
            print("!! 未检测到可见的 Steam 窗口，继续尝试（可能失败）")

    # 2. 打开控制台
    print("[2/5] 打开控制台 tab ...")
    ts_before = last_output_ts(read_logs())
    open_console()
    time.sleep(6)

    # 3. 自动输入 licenses_print
    print("[3/5] 自动输入 licenses_print ...")
    ok = try_auto_input()
    if ok:
        print("    已自动输入，等待日志更新 ...")
        ts_new = wait_log_update(ts_before)
        if ts_new:
            print(f"    日志已更新（{ts_new}）")
        else:
            print("    自动输入后未检测到日志更新")
            ok = False

    # 3b. 降级：手动输入
    if not ok:
        print("\n    !! 自动输入失败，请手动操作：")
        print("       1) Steam 客户端里打开『控制台』tab（Win+R 输入 steam://open/console）")
        print("       2) 点击底部输入框，输入 licenses_print 并回车")
        print("       3) 看到 License packageID 输出后，回到这里按回车继续")
        try:
            input("\n    完成后按回车继续 ...")
        except EOFError:
            pass
        ts_new = wait_log_update(ts_before, timeout=60)
        if not ts_new:
            print("!! 仍未检测到新输出，将使用日志中已有的最后一次输出")
        else:
            print(f"    日志已更新（{ts_new}）")

    # 4. 流水线
    ok1 = run_script("4a/5", os.path.join(BASE, "parse_appinfo.py"))
    ok2 = run_script("4b/5", os.path.join(BASE, "build_library.py"))
    ok3 = run_script("4c/5", os.path.join(BASE, "finalize_names.py"))

    # 5. 摘要
    print("\n=== 完成 ===")
    if ok1 and ok2 and ok3:
        lib = os.path.join(BASE, "steam_library.json")
        rows = __import__("json").load(open(lib, encoding="utf-8"))
        games = [r for r in rows if r["app_type"].lower() == "game"]
        own = [r for r in games if r["source"] == "own"]
        shared = [r for r in games if r["source"] == "family_shared"]
        print(f"总条目 {len(rows)} | 游戏 {len(games)}（自有 {len(own)} + 家庭共享 {len(shared)}）")
        print(f"输出：steam_library.json / steam_library.csv（游戏列表请用 Excel 筛选 app_type=game）")
    else:
        print("部分步骤失败，请检查上方输出")


if __name__ == "__main__":
    main()
