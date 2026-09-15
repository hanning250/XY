# -*- coding: utf-8 -*-
import hashlib
import re
import urllib.error
import urllib.request

IP, USER, PWD = "192.168.1.64", "admin", "STSXY304"


def digest(method, uri, www_auth, user, pwd):
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
            return resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        hdr = digest("GET", path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req = urllib.request.Request(url, headers={"Authorization": hdr})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")


def main():
    print(get("/ISAPI/Event/notification/httpHosts/1"))
    print("---")
    block = get("/ISAPI/Event/triggers")
    for m in re.finditer(r"<EventTrigger>.*?AIOP_Polling_Snap.*?</EventTrigger>", block, flags=re.S):
        print(m.group(0)[:1200])


if __name__ == "__main__":
    main()
