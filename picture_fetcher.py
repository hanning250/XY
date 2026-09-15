# -*- coding: utf-8 -*-
"""从告警 JSON/XML 或设备 URL 拉取抓拍图片。"""
import hashlib
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, List, Optional
from xml.etree import ElementTree

from event_parser import make_picture_name

URL_PATTERN = re.compile(
    r"https?://[^\s\"'<>]+|/(?:ISAPI|SDK|doc)/[^\s\"'<>]+",
    re.IGNORECASE,
)
URL_FIELD_HINTS = (
    "pictureurl",
    "imageurl",
    "picurl",
    "url",
    "bkgurl",
    "visiblelighturl",
    "thermalurl",
    "snapurl",
    "backgroundimage",
)


def _digest_auth_header(method: str, uri: str, www_auth: str, user: str, pwd: str) -> str:
    auth = dict(re.findall(r'(\w+)="?([^",]+)"?', www_auth.split(" ", 1)[1]))
    realm, nonce = auth["realm"], auth["nonce"]
    ha1 = hashlib.md5(f"{user}:{realm}:{pwd}".encode()).hexdigest()
    ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
    response = hashlib.md5(f"{ha1}:{nonce}:00000001:xyz:auth:{ha2}".encode()).hexdigest()
    return (
        f'Digest username="{user}", realm="{realm}", nonce="{nonce}", uri="{uri}", '
        f'algorithm=MD5, qop=auth, nc=00000001, cnonce="xyz", response="{response}"'
    )


def _normalize_url(url: str, device_ip: Optional[str]) -> Optional[str]:
    url = (url or "").strip()
    if not url or url in ("/", "0.0.0.0"):
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/") and device_ip:
        return f"http://{device_ip}{url}"
    return None


def extract_picture_urls(raw_text: str) -> List[str]:
    if not raw_text:
        return []

    found: List[str] = []
    text = raw_text.strip()

    if text.startswith("<"):
        try:
            root = ElementTree.fromstring(text)
            for node in root.iter():
                local = node.tag.split("}")[-1] if "}" in node.tag else node.tag
                if local.lower() in URL_FIELD_HINTS and node.text:
                    found.append(node.text.strip())
        except ElementTree.ParseError:
            pass
    elif text.startswith("{") or text.startswith("["):
        for match in URL_PATTERN.finditer(text):
            found.append(match.group(0))
        for key_match in re.finditer(
            r'"(?:pictureURL|imageURL|picUrl|url|bkgUrl|visibleLightURL|thermalURL)"\s*:\s*"([^"]+)"',
            text,
            flags=re.IGNORECASE,
        ):
            found.append(key_match.group(1))

    for match in URL_PATTERN.finditer(text):
        found.append(match.group(0))

    deduped = []
    seen = set()
    for item in found:
        item = item.strip().rstrip(",;")
        if item and item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _download_once(url: str, username: str, password: str, timeout: int = 12) -> bytes:
    path = urllib.parse.urlparse(url).path or "/"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            data = resp.read()
            if data and len(data) > 128:
                return data
            return b""
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            raise
        hdr = _digest_auth_header("GET", path, exc.headers.get("WWW-Authenticate", ""), username, password)
        request2 = urllib.request.Request(url, headers={"Authorization": hdr})
        with urllib.request.urlopen(request2, timeout=timeout) as resp:
            return resp.read()


def download_picture(url: str, device_ip: str, username: str, password: str) -> bytes:
    normalized = _normalize_url(url, device_ip)
    if not normalized:
        return b""
    try:
        return _download_once(normalized, username, password)
    except Exception as exc:
        print(f"[picture-fetcher] 下载失败 url={normalized}: {exc}")
        return b""


def save_picture_bytes(picture_dir: str, prefix: str, index: int, data: bytes) -> Optional[str]:
    if not data or len(data) < 128:
        return None
    if data[:3] == b"\xff\xd8\xff":
        ext = ".jpg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        ext = ".png"
    else:
        ext = ".jpg"
    name = make_picture_name(prefix, index).rsplit(".", 1)[0] + ext
    path = os.path.join(picture_dir, name)
    with open(path, "wb") as fp:
        fp.write(data)
    return path


def fetch_alarm_pictures(
    picture_dir: str,
    device_ip: str,
    embedded_pictures: Iterable[bytes],
    raw_text: str,
    remote_urls: Iterable[str],
    auth: dict,
) -> List[str]:
    paths: List[str] = []
    username = auth.get("username", "admin")
    password = auth.get("password", "")

    for index, pic_bytes in enumerate(embedded_pictures or []):
        saved = save_picture_bytes(picture_dir, "isup", index, pic_bytes)
        if saved:
            paths.append(saved)
            print(f"[picture-fetcher] 内嵌图片已保存 {os.path.basename(saved)} ({len(pic_bytes)} bytes)")

    url_candidates = list(remote_urls or []) + extract_picture_urls(raw_text or "")
    seen = set()
    remote_index = 0
    for url in url_candidates:
        if url in seen:
            continue
        seen.add(url)
        data = download_picture(url, device_ip, username, password)
        saved = save_picture_bytes(picture_dir, "remote", remote_index, data)
        if saved:
            paths.append(saved)
            print(f"[picture-fetcher] URL 图片已保存 {os.path.basename(saved)}")
            remote_index += 1

    return paths
