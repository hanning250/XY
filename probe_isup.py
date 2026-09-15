# -*- coding: utf-8 -*-
import hashlib
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

USER, PWD = "admin", "STSXY304"
IPS = ["192.168.1.10", "192.168.1.64"]


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


def req(ip, path, method="GET", body=None):
    url = f"http://{ip}{path}"
    data = body.encode("utf-8") if body else None
    request = urllib.request.Request(url, data=data, method=method)
    if body:
        request.add_header("Content-Type", "application/xml")
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="ignore")
        if exc.code != 401:
            return exc.code, body_text
        hdr = digest_auth_header(method, path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        request2 = urllib.request.Request(url, data=data, method=method, headers={"Authorization": hdr})
        if body:
            request2.add_header("Content-Type", "application/xml")
        with urllib.request.urlopen(request2, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def build_put_xml(ip, device_id):
    if ip.endswith(".10"):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<Ehome version="2.0" xmlns="http://www.hikvision.com/ver20/XMLSchema">
<enabled>true</enabled>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>192.168.1.100</ipAddress>
<portNo>7660</portNo>
<deviceID>{device_id}</deviceID>
<password>{PWD}</password>
<protocolVersion>v5.0</protocolVersion>
</Ehome>"""
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<Ehome xmlns="urn:selfextension:psiaext-ver10-xsd">
<enabled>true</enabled>
<addressingFormatType>ipaddress</addressingFormatType>
<ipAddress>192.168.1.100</ipAddress>
<portNo>7660</portNo>
<deviceID>{device_id}</deviceID>
<password>{PWD}</password>
<protocolVersion>v5.0</protocolVersion>
</Ehome>"""


def main():
    tests = [
        "/ISAPI/System/Network/Ehome",
        "/ISAPI/System/Network/Ehome/capabilities",
        "/ISAPI/System/Network/Ehome/status",
        "/ISAPI/System/Network/Ehome/test",
    ]
    for ip in IPS:
        print(f"\n######## {ip} ########")
        for path in tests:
            try:
                code, body = req(ip, path)
                print(f"[GET {path}] {code}")
                if body.strip():
                    print(body[:500])
            except Exception as exc:
                print(f"[GET {path}] ERR {exc}")
        device_id = "HaiKang-1" if ip.endswith(".10") else "box001"
        put_xml = build_put_xml(ip, device_id)
        for path in ("/ISAPI/System/Network/Ehome",):
            code, body = req(ip, path, "PUT", put_xml)
            print(f"[PUT {path}] {code}")
            print(body[:500])
        for path in ("/ISAPI/System/Network/Ehome/test",):
            try:
                code, body = req(ip, path, "PUT", put_xml)
                print(f"[PUT {path}] {code}")
                print(body[:500])
            except Exception as exc:
                print(f"[PUT {path}] ERR {exc}")
        code, body = req(ip, "/ISAPI/System/Network/Ehome")
        m = re.search(r"<registerStatus>([^<]+)</registerStatus>", body)
        print("registerStatus =", m.group(1) if m else "unknown")


if __name__ == "__main__":
    main()
