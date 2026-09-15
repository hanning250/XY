# -*- coding: utf-8 -*-
import hashlib
import re
import urllib.error
import urllib.request

IP = "192.168.1.64"
USER, PWD = "admin", "STSXY304"

PATHS = [
    "/ISAPI/Event/triggers",
    "/ISAPI/Event/triggersCap",
    "/ISAPI/Event/schedules",
    "/ISAPI/Event/notification/subscribeEvent",
    "/ISAPI/Event/notification/subscribeEventCap",
    "/ISAPI/Smart/Event/channels/1",
    "/ISAPI/Intelligent/channels/1/capabilities",
    "/ISAPI/Intelligent/channels/1/behaviorRule/1",
    "/ISAPI/Intelligent/channels/1/behaviorRule/1/linkage",
    "/ISAPI/ContentMgmt/search",
    "/ISAPI/System/Video/inputs/channels/1/motionDetection",
    "/ISAPI/Event/notification/httpHosts/1",
    "/ISAPI/Event/notification/httpHosts/1/test",
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


def request(ip, path, method="GET", body=None):
    url = f"http://{ip}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", "application/xml")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return exc.code, exc.read().decode("utf-8", errors="ignore")
        hdr = digest_auth_header(method, path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req2 = urllib.request.Request(url, data=data, method=method, headers={"Authorization": hdr})
        if body:
            req2.add_header("Content-Type", "application/xml")
        with urllib.request.urlopen(req2, timeout=10) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")


def main():
    for path in PATHS:
        try:
            code, body = request(IP, path)
            print(f"\n===== [{code}] {path} =====")
            print(body[:2000] if body else "(empty)")
        except Exception as exc:
            print(f"\n===== [ERR] {path} =====")
            print(exc)


if __name__ == "__main__":
    main()
