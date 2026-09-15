# -*- coding: utf-8 -*-
"""将 NVR/摄像头的事件上传中心改为 HTTP 推送到本后端。"""
import sys
import urllib.request

from isapi_client import load_config, request


TARGETS = [
    ("NVR", "192.168.1.64"),
    ("Camera", "192.168.1.10"),
]


def _platform_settings():
    cfg = load_config()
    api = cfg.get("api", {})
    http = cfg.get("http_notify", {})
    return (
        http.get("platform_ip", "192.168.1.100"),
        int(http.get("port") or api.get("port", 8080)),
        http.get("path", "/api/hikvision/event"),
    )


def build_http_host_xml(ip: str, platform_ip: str, api_port: int, event_path: str) -> str:
    if ip.endswith(".64"):
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
<HttpHostNotification version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
<id>1</id>
<url>{event_path}</url>
<protocolType>HTTP</protocolType>
<parameterFormatType>XML</parameterFormatType>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>{platform_ip}</ipAddress>
<portNo>{api_port}</portNo>
<httpAuthenticationMethod>none</httpAuthenticationMethod>
</HttpHostNotification>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotification version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>1</id>
<url>{event_path}</url>
<protocolType>HTTP</protocolType>
<parameterFormatType>XML</parameterFormatType>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>{platform_ip}</ipAddress>
<portNo>{api_port}</portNo>
<httpAuthenticationMethod>none</httpAuthenticationMethod>
</HttpHostNotification>"""


def verify_http_host(body: str, platform_ip: str, api_port: int, event_path: str) -> bool:
    checks = (
        "<protocolType>HTTP</protocolType>" in body,
        f"<ipAddress>{platform_ip}</ipAddress>" in body,
        f"<portNo>{api_port}</portNo>" in body,
        f"<url>{event_path}</url>" in body,
    )
    return all(checks)


def main():
    platform_ip, api_port, event_path = _platform_settings()
    print(f"配置 HTTP 事件上报 -> http://{platform_ip}:{api_port}{event_path}")
    ok_all = True
    for label, ip in TARGETS:
        print(f"\n===== {label} {ip} =====")
        code, body = request(
            ip,
            "/ISAPI/Event/notification/httpHosts/1",
            "PUT",
            build_http_host_xml(ip, platform_ip, api_port, event_path),
        )
        print(f"[PUT httpHosts/1] {code}")
        print(body[:500] if body else "")
        code, body = request(ip, "/ISAPI/Event/notification/httpHosts/1")
        print(f"[GET httpHosts/1] {code}")
        print(body[:800] if body else "")
        if code != 200 or not verify_http_host(body, platform_ip, api_port, event_path):
            ok_all = False
            print(f"[WARN] {label} HTTP 上传中心配置未生效，请检查 Web 界面")
        else:
            print(f"[OK] {label} 已切换为 HTTP 上报")
    print("\n--- 验证后端连通性（模拟 NVR POST）---")
    try:
        sample = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<EventNotificationAlert>"
            "<eventType>AIOP_Polling_Snap</eventType>"
            "<channelID>1</channelID>"
            "<dateTime>2026-09-14T16:30:00+08:00</dateTime>"
            "<eventDescription>HTTP配置验证</eventDescription>"
            "</EventNotificationAlert>"
        ).encode("utf-8")
        req = urllib.request.Request(
            f"http://{platform_ip}:{api_port}{event_path}",
            data=sample,
            method="POST",
            headers={"Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            print(f"[OK] 后端响应 {resp.status}: {resp.read().decode('utf-8', errors='ignore')}")
    except Exception as exc:
        ok_all = False
        print(f"[ERR] 无法访问后端 {platform_ip}:{api_port}{event_path}: {exc}")
        print("      请执行: python main.py --force  并检查防火墙 TCP 8080 入站")
    if ok_all:
        print("\n完成。请在 NVR 前触发一次 AI 告警，终端应出现 [http-event] 收到事件")
    else:
        print("\n部分步骤失败，请根据上方 WARN/ERR 处理。")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
