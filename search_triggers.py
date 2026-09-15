# -*- coding: utf-8 -*-
import hashlib
import re
import urllib.error
import urllib.request

IP = "192.168.1.64"
USER, PWD = "admin", "STSXY304"
KEYWORDS = ("AI", "capture", "polling", "snap", "VMD", "behavior", "rule", "helmet", "vest", "IO", "center")


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
        with urllib.request.urlopen(url, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        hdr = digest_auth_header("GET", path, exc.headers.get("WWW-Authenticate", ""), USER, PWD)
        req = urllib.request.Request(url, headers={"Authorization": hdr})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")


def main():
    body = get("/ISAPI/Event/triggers")
    blocks = re.findall(r"<EventTrigger>.*?</EventTrigger>", body, flags=re.S)
    print(f"total triggers: {len(blocks)}")
    for block in blocks:
        if any(k.lower() in block.lower() for k in KEYWORDS):
            print("\n--- match ---")
            print(block[:1500])
    for block in blocks:
        if "EventTriggerNotificationList" in block and "<EventTriggerNotification>" in block:
            et = re.search(r"<eventType>([^<]+)</eventType>", block)
            print("\n--- has notification ---", et.group(1) if et else "?")
            print(block[:1200])


if __name__ == "__main__":
    main()
