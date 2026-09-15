# -*- coding: utf-8 -*-
"""检查设备是否配置了事件上传中心（ISUP 平台侧）。"""
import hashlib
import re
import urllib.error
import urllib.request

USER, PWD = "admin", "STSXY304"
IPS = ["192.168.1.64", "192.168.1.10"]

PATHS = [
    "/ISAPI/Event/notification/httpHosts",
    "/ISAPI/Event/notification/httpHosts/capabilities",
    "/ISAPI/Event/notification/uploadCenter",
    "/ISAPI/Event/notification/uploadCenter/capabilities",
    "/ISAPI/System/Network/Ehome",
    "/ISAPI/ContentMgmt/InputProxy/channels",
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


def get(ip, path):
    url = f"http://{ip}{path}"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return exc.code, exc.read().decode("utf-8", errors="ignore")
        hdr = digest_auth_header("GET", path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req = urllib.request.Request(url, headers={"Authorization": hdr})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def main():
    for ip in IPS:
        print(f"\n========== {ip} ==========")
        for path in PATHS:
            try:
                code, body = get(ip, path)
                print(f"\n[{code}] {path}")
                if body.strip():
                    print(body[:1200])
            except Exception as exc:
                print(f"\n[ERR] {path}: {exc}")


if __name__ == "__main__":
    main()
