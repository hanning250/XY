# -*- coding: utf-8 -*-
"""将 NVR/摄像头的事件上传中心改为 HTTP 推送到本后端（8080）。"""
import hashlib
import re
import sys
import urllib.error
import urllib.request

USER, PWD = "admin", "STSXY304"
PLATFORM_IP = "192.168.1.100"
API_PORT = 8080
EVENT_PATH = "/api/hikvision/event"

TARGETS = [
    ("NVR", "192.168.1.64"),
    ("Camera", "192.168.1.10"),
]


def digest_auth_header(method, uri, www_auth, user, pwd):
    auth = dict(re.findall(r'(\w+)="?([^",]+)"?', www_auth.split(" ", 1)[1]))
    realm, nonce = auth["realm"], auth["nonce"]
    ha1 = hashlib.md5(f"{user}:{realm}:{pwd}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    response = hashlib.md5(f"{ha1}:{nonce}:00000001:xyz:auth:{ha2}".encode()).hexdigest()
    return (
        f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
        f'algorithm=MD5, qop=auth, nc=00000001, cnonce="xyz", response="{response}"'
    )


def request(ip, path, method="GET", body=None, content_type="application/xml"):
    url = f"http://{ip}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return exc.code, exc.read().decode("utf-8", errors="ignore")
        hdr = digest_auth_header(method, path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req2 = urllib.request.Request(url, data=data, method=method, headers={"Authorization": hdr})
        if body:
            req2.add_header("Content-Type", content_type)
        with urllib.request.urlopen(req2, timeout=12) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def build_http_host_xml(ip: str) -> str:
    if ip.endswith(".64"):
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
<HttpHostNotification version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
<id>1</id>
<url>{EVENT_PATH}</url>
<protocolType>HTTP</protocolType>
<parameterFormatType>XML</parameterFormatType>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>{PLATFORM_IP}</ipAddress>
<portNo>{API_PORT}</portNo>
<httpAuthenticationMethod>none</httpAuthenticationMethod>
</HttpHostNotification>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotification version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<id>1</id>
<url>{EVENT_PATH}</url>
<protocolType>HTTP</protocolType>
<parameterFormatType>XML</parameterFormatType>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>{PLATFORM_IP}</ipAddress>
<portNo>{API_PORT}</portNo>
<httpAuthenticationMethod>none</httpAuthenticationMethod>
</HttpHostNotification>"""


def verify_http_host(body: str) -> bool:
    checks = (
        "<protocolType>HTTP</protocolType>" in body,
        f"<ipAddress>{PLATFORM_IP}</ipAddress>" in body,
        f"<portNo>{API_PORT}</portNo>" in body,
        f"<url>{EVENT_PATH}</url>" in body,
    )
    return all(checks)


def main():
    print(f"配置 HTTP 事件上报 -> http://{PLATFORM_IP}:{API_PORT}{EVENT_PATH}")
    ok_all = True
    for label, ip in TARGETS:
        print(f"\n===== {label} {ip} =====")
        code, body = request(ip, "/ISAPI/Event/notification/httpHosts/1", "PUT", build_http_host_xml(ip))
        print(f"[PUT httpHosts/1] {code}")
        print(body[:500] if body else "")
        code, body = request(ip, "/ISAPI/Event/notification/httpHosts/1")
        print(f"[GET httpHosts/1] {code}")
        print(body[:800] if body else "")
        if code != 200 or not verify_http_host(body):
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
            f"http://{PLATFORM_IP}:{API_PORT}{EVENT_PATH}",
            data=sample,
            method="POST",
            headers={"Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            print(f"[OK] 后端响应 {resp.status}: {resp.read().decode('utf-8', errors='ignore')}")
    except Exception as exc:
        ok_all = False
        print(f"[ERR] 无法访问后端 {PLATFORM_IP}:{API_PORT}{EVENT_PATH}: {exc}")
        print("      请执行: python main.py --force  并检查防火墙 TCP 8080 入站")
    if ok_all:
        print("\n完成。请在 NVR 前触发一次 AI 告警，终端应出现 [http-event] 收到事件 from 192.168.1.64")
    else:
        print("\n部分步骤失败，请根据上方 WARN/ERR 处理。")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
