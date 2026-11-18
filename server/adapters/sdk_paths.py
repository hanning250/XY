# -*- coding: utf-8 -*-
"""SDK 路径与导入适配（跨平台版：Windows + Linux 都支持）。

现有代码用 `from src.Common import glo` 等包内绝对导入。
这里统一处理：把项目根加入 sys.path，并校验目录结构。

★ 变更：本文件原先是 Windows 专用（直接拒绝非 Windows）。
  现在改为按平台选择要检查的动态库：
    Windows → HCISUPCMS.dll 等（开发机演示用）
    Linux   → libHCISUPCMS.so 等（海康 V2.5.1.35 Linux64 包提供，Docker 部署用）
  这样同一份代码在开发机（Windows）和服务器（Ubuntu 容器）上都能跑。
"""

from __future__ import annotations

import logging
import platform
import sys

from server.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


def ensure_src_importable() -> None:
    """让 `import src.*` 可用。

    现有代码以 `src` 为顶层包；服务化后必须显式把项目根加进 sys.path。
    """
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


# ---------------------------------------------------------------------------
# 平台相关的动态库清单
# ---------------------------------------------------------------------------
# 各平台「SDK 运行必需」的动态库。缺任何一个，对应服务就起不来。
_REQUIRED_LIBS = {
    "windows": [
        "HCISUPCMS.dll",       # CMS 设备注册
        "HCISUPAlarm.dll",     # AMS 告警
        "HCISUPSS.dll",        # SS 图片存储
        "HCISUPStream.dll",    # SMS 流媒体
    ],
    "linux": [
        "libHCISUPCMS.so",     # CMS 设备注册
        "libHCISUPAlarm.so",   # AMS 告警
        "libHCISUPSS.so",      # SS 图片存储
        "libHCISUPStream.so",  # SMS 流媒体
        "libcrypto.so",        # OpenSSL（对应 Windows 的 libeay32.dll）
        "libssl.so",           # OpenSSL（对应 Windows 的 ssleay32.dll）
        "libsqlite3.so",       # SQLite（SS 服务依赖）
    ],
}

# 仅提醒、不算致命缺失的库（缺了通常是部分功能受限）
_OPTIONAL_LIBS = {
    "linux": [
        "libHCNetUtils.so",       # 网络工具，部分 ISAPI 透传用
        "libNPQos.so",            # 流媒体 QoS
        "libhpr.so",              # 海康私有库
        "libz.so",                # zlib
        "libSystemTransform.so",  # 转码辅助
        "libiconv2.so",           # 字符集转换
    ],
    "windows": [],
}


def current_platform() -> str:
    """返回 'windows' / 'linux' / 其他。"""
    return platform.system().lower()


def arch_label() -> str:
    """返回 src/ 代码里用的 system_type 值，如 'linux64'。

    必须与 src/SdkService/**/HCISUP*.py 里 system_type 的计算方式一致，
    否则那边的字典会 KeyError。
    """
    import re

    sys_platform = platform.system().lower().strip()
    python_bit = platform.architecture()[0]
    m = re.findall(r"(\d+)\w*", python_bit)
    bit = m[0] if m else "64"
    return f"{sys_platform}{bit}"


def sdk_available() -> tuple[bool, str]:
    """检查 ISUP SDK 是否可用（当前平台的动态库是否就位）。"""
    plat = current_platform()

    if plat not in _REQUIRED_LIBS:
        return (
            False,
            f"不支持的操作系统: {platform.system()}。"
            "海康 ISUP SDK 仅提供 Windows 和 Linux x86_64 版本。",
        )

    # 架构检查：海康 Linux 包只有 x86_64
    if plat == "linux":
        machine = platform.machine().lower()
        if machine not in ("x86_64", "amd64"):
            return (
                False,
                f"CPU 架构 {machine} 不受支持。海康 ISUP SDK 只提供 x86_64(Linux64) 版本，"
                "ARM64 服务器（华为鲲鹏/飞腾等）无法运行。",
            )

    lib_dir = PROJECT_ROOT / "lib"
    if not lib_dir.is_dir():
        return False, f"SDK 目录不存在: {lib_dir}"

    required = _REQUIRED_LIBS[plat]
    missing = [f for f in required if not (lib_dir / f).exists()]
    if missing:
        hint = (
            "请从海康 HCISUPSDKV*_Linux64_ZH 包的 lib 目录拷贝这些文件到 lib/ 下"
            if plat == "linux"
            else "请把开发包 lib64 目录下的 DLL 拷贝到 lib/ 下"
        )
        return False, f"缺少 SDK 动态库: {', '.join(missing)}（{hint}）"

    # Linux 还需要 HCAapSDKCom 目录（放组件依赖 .so）
    com_dir = lib_dir / "HCAapSDKCom"
    if plat == "linux":
        if not com_dir.is_dir() or not any(com_dir.iterdir()):
            return False, f"缺少组件目录或目录为空: {com_dir}"
    elif not com_dir.is_dir():
        return False, f"缺少组件目录: {com_dir}"

    conf = PROJECT_ROOT / "resources" / "conf" / "isupConf.json"
    if not conf.exists():
        return False, f"缺少配置文件: {conf}"

    # 可选库缺失只提示不阻断
    optional_missing = [
        f for f in _OPTIONAL_LIBS.get(plat, [])
        if not (lib_dir / f).exists()
    ]
    if optional_missing:
        logger.warning(
            "以下可选动态库缺失，部分次要功能可能不可用: %s",
            ", ".join(optional_missing),
        )

    return True, f"ok ({arch_label()})"


def diagnose() -> str:
    """生成可读的诊断报告，出问题时一眼看出缺什么。"""
    plat = current_platform()
    lib_dir = PROJECT_ROOT / "lib"

    lines = [
        "=" * 62,
        "  ISUP SDK 平台诊断",
        "=" * 62,
        f"  操作系统   : {platform.system()} {platform.release()}",
        f"  CPU 架构   : {platform.machine()}",
        f"  Python     : {platform.python_version()} ({platform.architecture()[0]})",
        f"  平台标识   : {arch_label()}",
        f"  SDK 目录   : {lib_dir}",
    ]

    if lib_dir.is_dir():
        files = sorted(p.name for p in lib_dir.iterdir() if p.is_file())
        so_files = [f for f in files if ".so" in f]
        dll_files = [f for f in files if f.endswith(".dll")]
        lines.append(f"  .so 文件   : {len(so_files)} 个")
        lines.append(f"  .dll 文件  : {len(dll_files)} 个")
        if so_files:
            lines.append(f"  已就位     : {', '.join(sorted(so_files))}")
    else:
        lines.append("  ⚠️ SDK 目录不存在")

    ok, reason = sdk_available()
    lines.append("-" * 62)
    lines.append(f"  结论       : {'✅ SDK 可用' if ok else '❌ SDK 不可用'}")
    lines.append(f"  说明       : {reason}")

    # 平台明显不匹配时给出针对性提示
    if not ok:
        if plat == "linux" and (lib_dir / "HCISUPCMS.dll").exists() and \
                not (lib_dir / "libHCISUPCMS.so").exists():
            lines += [
                "",
                "  ⚠️ lib/ 下是 Windows 的 .dll，但当前运行在 Linux 上。",
                "     Windows DLL 无法在 Linux 加载，必须换成 .so 文件。",
                "     来源：海康 HCISUPSDKV2.5.1.35_build20241101_Linux64_ZH 的 lib/ 目录。",
            ]
        elif plat == "windows" and (lib_dir / "libHCISUPCMS.so").exists() and \
                not (lib_dir / "HCISUPCMS.dll").exists():
            lines += [
                "",
                "  ⚠️ lib/ 下只有 Linux 的 .so，但当前运行在 Windows 上。",
                "     Windows 需要 .dll 文件。",
            ]

    lines.append("=" * 62)
    return "\n".join(lines)
