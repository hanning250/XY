# -*- coding: utf-8 -*-
"""海康 ISAPI Digest 认证客户端（供配置/诊断脚本复用）。"""
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from typing import Optional, Tuple

_ROOT = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_ROOT, "config.json")


def load_config() -> dict:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    with open(_CONFIG_PATH, "r", encoding="utf-8") as fp:
        return json.load(fp)


def device_credentials() -> Tuple[str, str]:
    auth = load_config().get("device_auth", {})
    return auth.get("username", "admin"), auth.get("password", "")


def digest_auth_header(method: str, uri: str, www_auth: str, user: str, pwd: str) -> str:
    auth = dict(re.findall(r'(\w+)="?([^",]+)"?', www_auth.split(" ", 1)[1]))
    realm, nonce = auth["realm"], auth["nonce"]
    ha1 = hashlib.md5(f"{user}:{realm}:{pwd}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    response = hashlib.md5(f"{ha1}:{nonce}:00000001:xyz:auth:{ha2}".encode()).hexdigest()
    return (
        f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
        f'algorithm=MD5, qop=auth, nc=00000001, cnonce="xyz", response="{response}"'
    )


def request(
    ip: str,
    path: str,
    method: str = "GET",
    body: Optional[str] = None,
    content_type: str = "application/xml",
    user: Optional[str] = None,
    pwd: Optional[str] = None,
    timeout: int = 12,
) -> Tuple[int, str]:
    if user is None or pwd is None:
        user, pwd = device_credentials()
    url = f"http://{ip}{path}"
    data = body.encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    if body:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return exc.code, exc.read().decode("utf-8", errors="ignore")
        hdr = digest_auth_header(method, path, exc.headers.get("WWW-Authenticate", ""), user, pwd)
        req2 = urllib.request.Request(url, data=data, method=method, headers={"Authorization": hdr})
        if body:
            req2.add_header("Content-Type", content_type)
        with urllib.request.urlopen(req2, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="ignore")
