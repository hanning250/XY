# -*- coding: utf-8 -*-
import hashlib
import re
import urllib.error
import urllib.request

IP = "192.168.1.10"
USER, PWD = "admin", "STSXY304"
PATHS = [
    "/ISAPI/Event/triggers",
    "/ISAPI/Smart/Event/channels/1",
    "/ISAPI/Intelligent/channels/1/capabilities",
    "/ISAPI/Intelligent/channels/1/behaviorRule/1",
    "/ISAPI/Intelligent/channels/1/behaviorRule/1/linkage",
    "/ISAPI/System/Network/Ehome",
    "/ISAPI/Event/notification/httpHosts",
    "/ISAPI/SDT/Management/Task/1",
    "/ISAPI/SDT/Management/Task",
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


def get(path):
    url = f"http://{IP}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return exc.code, exc.read().decode("utf-8", errors="ignore")
        hdr = digest_auth_header("GET", path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req = urllib.request.Request(url, headers={"Authorization": hdr})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def main():
    for path in PATHS:
        try:
            code, body = get(path)
            print(f"\n===== [{code}] {path} =====")
            print(body[:2500] if body else "(empty)")
        except Exception as exc:
            print(f"\n===== [ERR] {path} =====\n{exc}")


if __name__ == "__main__":
    main()
