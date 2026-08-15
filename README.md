# steam-library-exporter

一键导出 Steam 账号的**完整游戏库列表**（含家庭共享游戏）为 JSON / CSV 的 Windows 小工具。

基于 Steam 官方控制台命令与本地缓存解析，纯本地读取、零网络请求、无硬性依赖。

## 特性

- **一键运行**：自动启动 Steam、打开控制台、通过 UI 自动化输入 `licenses_print`，全程无需手动操作
- **覆盖完整**：自有游戏 + 家庭共享游戏 + DLC / Tool / Demo / Music 等全部条目，附支付类型与许可证包 ID
- **纯本地读取**：只读 Steam 本地日志（`console_log.txt`）和 `appinfo.vdf`，**不联网、不上传任何数据**
- **路径自适应**：Steam 安装目录自动检测（注册表 + 默认路径），解压即用，无需修改任何配置
- **优雅降级**：缺少可选依赖或自动输入失败时，自动切换为手动操作指引，流程不中断
- **日志轮转兼容**：自动拼接 `console_log.txt` 与轮转文件，按时间戳定位最新一次输出

## 工作原理

```
Steam 控制台 licenses_print ──→ console_log.txt ──┐
                                                  ├──→ 合并解析 ──→ steam_library.json / csv
appcache/appinfo.vdf ──→ parse_appinfo.py ────────┘
                            （appid → 名称/类型映射）
```

1. 在 Steam 控制台执行 `licenses_print`，Steam 将全部许可证（packageID、支付类型、Apps 列表）写入本地日志
2. 解析 `appinfo.vdf` 得到 appid → 游戏名称 / 类型的映射表
3. 合并两者：按支付类型区分自有（own）与家庭共享（family_shared），自有优先去重
4. 为已下架 / 内部测试的 appid 填充占位名，输出最终列表

## Quick Start

### 环境要求

| 要求 | 说明 |
|---|---|
| 操作系统 | Windows 10 / 11 |
| Python | 3.10 及以上（3.10 ~ 3.12 自动探测） |
| Steam | 已安装 Steam 客户端（任意安装路径） |
| 依赖 | 无硬性依赖（`pywinauto` 可选，见下） |

### 运行步骤

```bash
# 1. 克隆仓库
git clone https://github.com/Redark12/steam-library-exporter.git
cd steam-library-exporter

# 2. （可选）安装自动输入依赖；不装也可运行，自动降级为手动模式
pip install -r requirements.txt

# 3. 运行（二选一）
run.bat          # 双击即可，自动探测 Python
py main.py       # 或直接命令行运行
```

运行后程序自动完成：

1. 启动 Steam（若未运行）并等待界面就绪
2. 打开控制台 tab（`steam://open/console`）
3. 通过 UI 自动化在控制台输入 `licenses_print`
4. 校验日志已更新 → 依次执行解析、合并、收尾三步流水线
5. 打印最终统计（总条目数、自有 / 共享游戏数）

> **自动输入失败？** 程序会打印手动操作指引：在 Steam 客户端打开控制台 tab，输入 `licenses_print` 回车，看到输出后回到命令行按回车继续，流水线照常执行。

### 输出文件

| 文件 | 内容 |
|---|---|
| `steam_library.json` | 完整库数据（appid、名称、类型、来源、许可证包、支付类型） |
| `steam_library.csv` | 同上，表格格式（Excel 可直接打开，UTF-8-BOM；筛选 `app_type` 列的 `game` 即可得到纯游戏列表） |

## 文件说明

| 文件 | 功能 |
|---|---|
| `main.py` | **入口脚本**。编排全流程：检测 / 启动 Steam → 打开控制台 → UIA 自动输入 `licenses_print` → 验证日志更新 → 依次调用三个子脚本 → 打印摘要。自动输入失败时降级为手动模式 |
| `steam_utils.py` | 公共工具：`find_steam_dir()` 从注册表 `HKCU\Software\Valve\Steam\SteamPath` 读取 Steam 安装目录（失败则回退默认路径）；`base_dir()` 返回脚本所在目录，保证项目可整体迁移 |
| `parse_appinfo.py` | 解析 Steam 客户端本地缓存 `appcache/appinfo.vdf`（新版二进制格式），提取全部 appid → 名称 / 类型映射，输出 `appinfo_map.json` |
| `build_library.py` | 核心合并脚本。读取（自动拼接轮转的）`console_log.txt`，按时间戳定位最新一次 `licenses_print` 输出，解析每个许可证的 packageID / 支付类型 / Apps 列表；按 "Family Group" 判定家庭共享，自有优先去重；结合 appinfo 映射输出 `steam_library.json` / `.csv` |
| `finalize_names.py` | 收尾脚本。为已下架 / 内部测试的 appid 填充占位名（与客户端库视图显示一致），重新生成 JSON / CSV 并打印最终统计与预览 |
| `pack_release.py` | 打包分享版：将源码与启动脚本打成 zip（自动排除个人游戏库数据文件），生成 `release/steam-library-tool.zip` |
| `run.bat` | Windows 双击启动脚本：自动探测 `py` 启动器 / Python 3.10~3.12 / PATH 中的 python，找不到时给出安装指引 |

## 常见问题

**Q：运行 `python main.py` 没有任何反应？**
Windows 11 的微软商店应用执行别名劫持了 `python` 命令。改用 `py main.py` 或双击 `run.bat`；或在 设置 → 应用 → 高级应用设置 → 应用执行别名 中关闭 `python.exe` 开关。

**Q：提示"未找到 Steam 安装目录"？**
Steam 安装在非默认路径且注册表无记录。请先正常启动一次 Steam 客户端（安装时会写入注册表），或自行设置 `HKCU\Software\Valve\Steam` 下的 `SteamPath`。

**Q：输出的数据里游戏名缺失 / 显示占位名？**
占位名 `AppID xxx (已下架/测试)` 表示该 app 已从商店下架或为内部测试应用，与 Steam 客户端库视图的显示一致，属正常现象。

**Q：数据没有更新？**
程序按日志时间戳定位最新一次 `licenses_print` 输出，请确认本次运行中"日志已更新"提示出现；若未出现，程序会降级提示手动输入，按提示操作后回车继续即可。

## 隐私说明

- 本工具**仅读取本地文件**（Steam 日志、appinfo.vdf），全程无任何网络请求，不会上传任何数据
- 运行产物（游戏库列表）仅保存在脚本所在目录，不会外传
- 仓库不含任何个人信息或游戏库数据（`steam_library.*`、`appinfo_map.json` 已加入 `.gitignore`）

## 合规说明

- 本项目为**开源、非商业**项目，仅作个人学习与自用
- 工具**仅读取本地文件**（Steam 日志、appinfo.vdf），不修改客户端、不注入进程、不绕过任何保护机制
- 使用的 `licenses_print` 是 Steam 官方控制台命令，等同用户手动输入；自动输入仅用于发送这一条命令，不涉及任何市场交易、账号创建等自动化行为
- 项目与 Valve 无关联，非官方工具；若对自动化输入有顾虑，可选择手动模式（程序内置降级指引）
- Steam 订户协议（SSA）可能更新，使用前请自行评估

## License

[MIT](LICENSE)
