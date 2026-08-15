# -*- coding: utf-8 -*-
"""公共工具：Steam 安装目录自动检测（支持项目迁移/分享）"""
import os


def find_steam_dir():
    """优先读注册表 SteamPath，失败则用默认安装路径"""
    default = r"C:\Program Files (x86)\Steam"
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            v, _ = winreg.QueryValueEx(k, "SteamPath")
        if v and os.path.isdir(v):
            return v
    except Exception:
        pass
    if os.path.isdir(default):
        return default
    return ""


def base_dir():
    """脚本所在目录（所有脚本与本文件同目录部署）"""
    return os.path.dirname(os.path.abspath(__file__))
