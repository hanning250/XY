# -*- coding: utf-8 -*-
"""Read ISUP config from devices and toggle enable to trigger re-registration."""
import hashlib
import re
import time
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

USER = "admin"
PWD = "STSXY304"
DEVICES = [
    ("192.168.1.10", "HaiKang-1"),
    ("192.168.1.64", "NVR"),
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


def isapi_request(ip, path, method="GET", body=None, content_type="application/xml"):
    url = f"http://{ip}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        hdr = digest_auth_header(method, path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req2 = urllib.request.Request(url, data=data, method=method, headers={"Authorization": hdr})
        if body:
            req2.add_header("Content-Type", content_type)
        with urllib.request.urlopen(req2, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def find_ehome_path(ip):
    for path in ("/ISAPI/System/Network/Ehome", "/ISAPI/System/Network/EHome"):
        try:
            code, body = isapi_request(ip, path)
            if code == 200 and body.strip():
                return path, body
        except Exception as exc:
            print(f"[{ip}] GET {path} failed: {exc}")
    return None, None


def patch_ehome_xml(xml_text, enabled: bool, device_id: str, key: str):
    root = ET.fromstring(xml_text)
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    def set_text(tag, value):
        node = root.find(f".//{ns}{tag}")
        if node is None:
            node = ET.SubElement(root, f"{ns}{tag}" if ns else tag)
        node.text = value

    set_text("enabled", "true" if enabled else "false")
    set_text("addressingFormatType", "ipaddress")
    set_text("ipAddress", "192.168.1.100")
    set_text("portNo", "7660")
    set_text("deviceID", device_id)
    for key_tag in ("key", "password", "ehomeKey", "registerKey"):
        node = root.find(f".//{ns}{key_tag}")
        if node is not None:
            node.text = key
    if root.find(f".//{ns}key") is None and root.find(f".//{ns}password") is None:
        set_text("key", key)
    return ET.tostring(root, encoding="unicode")


def main():
    for ip, device_id in DEVICES:
        print(f"\n===== {ip} ({device_id}) =====")
        path, body = find_ehome_path(ip)
        if not path:
            print("未找到 Ehome ISAPI 接口")
            continue
        print(body[:800])
        try:
            full_xml = patch_ehome_xml(body, True, device_id, PWD)
            code, resp = isapi_request(ip, path, "PUT", full_xml)
            print(f"apply   -> {code}: {resp[:300]}")
            code2, body2 = isapi_request(ip, path)
            print(f"status  -> {code2}")
            if "registerStatus" in body2:
                m = re.search(r"<registerStatus>([^<]+)</registerStatus>", body2)
                if m:
                    print(f"registerStatus={m.group(1)}")
        except Exception as exc:
            print(f"配置 ISUP 失败: {exc}")


if __name__ == "__main__":
    main()
