# -*- coding: utf-8 -*-
"""配置模板渲染 —— 把 isupConf.json 里的写死值改成环境变量驱动。

问题：resources/conf/isupConf.json 里 192.168.1.118 出现 12 次（开发机 IP）。
      甲方服务器网段必然不同，逐个手改容易漏。

做法：容器启动时用 entrypoint 脚本渲染这份模板，
      占位符 ${ISUP_SERVER_IP} 等从环境变量注入，生成真正的 isupConf.json。
      原文件保持不动（本模板是独立副本），所以本地演示不受影响。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 模板里的占位符写法：${VAR} 或 ${VAR:-默认值}
_VAR_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def _substitute(text: str, env: dict[str, str]) -> str:
    """替换 ${VAR} / ${VAR:-default}。"""

    def repl(m: re.Match) -> str:
        name = m.group(1)
        default = m.group(2)
        if name in env and env[name] != "":
            return env[name]
        if default is not None:
            return default
        logger.warning("环境变量 %s 未设置且无默认值，保留为空字符串", name)
        return ""

    return _VAR_PATTERN.sub(repl, text)


def _strip_json_comments(text: str) -> str:
    """isupConf.json 带 // 注释，标准 json 解析不了（沿用原 ConfRead 的做法）。"""
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )


def render_template(template_path: Path, output_path: Path, env: dict[str, str]) -> dict[str, Any]:
    """渲染模板并写出，返回解析后的 dict。

    先替换占位符再剥注释 —— 顺序不能反，注释里的占位符也要能替换。
    """
    if not template_path.is_file():
        raise FileNotFoundError(f"配置模板不存在: {template_path}")

    raw = template_path.read_text(encoding="utf-8")
    substituted = _substitute(raw, env)

    try:
        conf = json.loads(_strip_json_comments(substituted))
    except json.JSONDecodeError as exc:
        # 报错时把出问题的行打印出来，省得靠猜
        lines = _strip_json_comments(substituted).splitlines()
        ctx = ""
        if 0 < exc.lineno <= len(lines):
            ctx = f"\n  出错行 {exc.lineno}: {lines[exc.lineno - 1]}"
        raise ValueError(
            f"渲染后的 isupConf.json 不是合法 JSON: {exc.msg}{ctx}\n"
            "常见原因：环境变量里含未转义的双引号或反斜杠。"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(conf, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("已生成配置: %s", output_path)
    return conf


def validate_isup_conf(conf: dict[str, Any]) -> list[str]:
    """校验渲染后的配置是否自相矛盾。返回问题列表（空 = 通过）。"""
    problems: list[str] = []

    def get(path: str, default=None):
        cur: Any = conf
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    # --- 监听 IP 必须是本机能绑定的地址 ---
    # 0.0.0.0 是合法的（绑所有网卡），写具体 IP 时该 IP 必须真实存在
    listen_keys = [
        "cms.CmsServerIP",
        "ss.PicServerListenIP",
        "ams.AlarmServerListenIP",
        "sms.SmsServerListenIP",
        "sms.SmsBackServerListenIP",
    ]
    # 对外通告 IP —— 这些是设备要回连的地址，同样必须是合法 IP
    report_keys = [
        "cms.DasServerIP",
        "ss.PicServerIP",
        "ams.AlarmServerIP",
        "sms.SmsServerIP",
        "sms.SmsBackServerIP",
    ]

    for key in listen_keys + report_keys:
        val = get(key)
        if val is None:
            problems.append(f"缺少配置项: {key}")
            continue
        if val in ("0.0.0.0", ""):
            # 通告 IP 为空会导致设备无法回连，必须报错
            if key in report_keys:
                problems.append(
                    f"{key} 为空 —— 设备需要靠它回连平台，"
                    "请在环境变量里设置 ISUP_SERVER_IP"
                )
            continue
        if not _looks_like_ip(val):
            problems.append(f"{key} 不是合法 IP: {val}")

    # --- 上传地址 / 监听地址应一致（设备要能连到）---
    for listen_key, report_key in (
        ("cms.CmsServerIP", "cms.DasServerIP"),
        ("ss.PicServerListenIP", "ss.PicServerIP"),
        ("ams.AlarmServerListenIP", "ams.AlarmServerIP"),
        ("sms.SmsServerListenIP", "sms.SmsServerIP"),
    ):
        lv, rv = get(listen_key), get(report_key)
        if lv and rv and lv != rv and "0.0.0.0" not in (lv, rv):
            problems.append(
                f"{listen_key}({lv}) 与 {report_key}({rv}) 不一致。"
                "监听地址是 0.0.0.0 时可以不一致，否则设备可能回连失败。"
            )

    # --- 端口冲突检查 ---
    #
    # ⚠️ 重要：不能简单按「端口号重复」判断冲突！
    #    isupConf.json 的设计里，每个服务的「监听端口」和「对外通告端口」
    #    **本来就应该是同一个号**，例如：
    #        CmsServerPort = DasServerPort = 7661
    #        PicServerListenPort = PicServerPort = 6011
    #    这是正确配置，不是冲突。
    #
    #    真正的冲突是「**不同服务**用了同一个端口」。
    #    所以这里按「服务分组」取每组的代表端口，再跨组比对。
    #
    #    另外 UDP 7662 与 TCP 7663 是不同协议，同号也不冲突；
    #    甚至 AMS 的 UDP/TCP 用同号也是允许的。
    service_ports: dict[str, dict[str, int]] = {}

    # 服务名 -> [(协议, 端口配置键), ...]，同一服务内多个键视为同一端口
    service_groups = {
        "cms": [("tcp", "cms.CmsServerPort")],
        "ss": [("tcp", "ss.PicServerListenPort")],
        "ams_tcp": [("tcp", "ams.AlarmServerListenTCPPort")],
        "ams_udp": [("udp", "ams.AlarmServerListenUDPPort")],
        "sms": [("tcp", "sms.SmsServerListenPort")],
        "sms_back": [("tcp", "sms.SmsBackServerListenPort")],
    }

    for svc, entries in service_groups.items():
        proto, key = entries[0]
        val = get(key)
        if isinstance(val, int):
            service_ports[svc] = {"proto": proto, "port": val, "key": key}

    # 跨服务比对：只有「协议相同 且 端口相同」才算冲突
    seen: dict[tuple[str, int], str] = {}
    for svc, info in service_ports.items():
        sig = (info["proto"], info["port"])
        if sig in seen:
            other = seen[sig]
            problems.append(
                f"端口冲突：{svc}({info['key']}={info['port']}) 与 "
                f"{other} 使用了相同的 {info['proto'].upper()} 端口 {info['port']}。"
                "不同服务必须用不同端口。"
            )
        else:
            seen[sig] = f"{svc}({info['key']})"

    # 同一服务内监听/通告端口应一致（不一致多半是改漏了）
    for listen_key, report_key in (
        ("cms.CmsServerPort", "cms.DasServerPort"),
        ("ss.PicServerListenPort", "ss.PicServerPort"),
        ("ams.AlarmServerListenTCPPort", "ams.AlarmServerTCPPort"),
        ("ams.AlarmServerListenUDPPort", "ams.AlarmServerUDPPort"),
        ("sms.SmsServerListenPort", "sms.SmsServerPort"),
        ("sms.SmsBackServerListenPort", "sms.SmsBackServerPort"),
    ):
        lv, rv = get(listen_key), get(report_key)
        if isinstance(lv, int) and isinstance(rv, int) and lv != rv:
            problems.append(
                f"{listen_key}({lv}) 与 {report_key}({rv}) 不一致。"
                "监听端口与设备回连端口必须相同，否则设备连不上。"
            )

    # --- ISUPKey 不能是空的 ---
    if not get("ISUPKey"):
        problems.append("ISUPKey 为空 —— 必须与设备网页 ISUP 配置里的登录密钥一致")

    return problems


def _looks_like_ip(value: str) -> bool:
    parts = str(value).split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        if not p.isdigit() or not 0 <= int(p) <= 255:
            return False
    return True


# ---------------------------------------------------------------------------
# 端口冲突的外部检测（真实 bind 测试，比上面的一致性检查更硬）
# ---------------------------------------------------------------------------
def check_ports_available(ports: list[tuple[str, int]]) -> list[str]:
    """尝试真实 bind，返回被占用的端口列表。容器启动时跑一次。"""
    import socket

    problems: list[str] = []
    for proto, port in ports:
        sock_type = socket.SOCK_STREAM if proto == "tcp" else socket.SOCK_DGRAM
        s = socket.socket(socket.AF_INET, sock_type)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("0.0.0.0", port))
        except OSError as exc:
            problems.append(f"{proto.upper()} {port} 无法绑定: {exc}")
        finally:
            s.close()
    return problems
