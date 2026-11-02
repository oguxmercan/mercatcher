#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - FileMoon Çıkarıcı (Extractor)
filemoon.sx, filemoon.to, filemoon.in vb. servislerden video indirir.
"""

import re
import urllib.parse
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename
from .js_unpacker import unpack_js

class FileMoonExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_filemoon_url(self, url: str) -> bool:
        return any(d in url for d in [
            "filemoon.sx", "filemoon.to", "filemoon.in", "filemoon.link", "filemoon.art"
        ])

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc

        # /d/ -> /e/ çevir
        embed_url = re.sub(r"/d/([a-zA-Z0-9]+)", r"/e/\1", url)
        if not embed_url.startswith("http"):
            embed_url = f"https://{netloc}{embed_url}"

        self.log(f"[*] FileMoon taranıyor: {embed_url}")
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": f"https://{netloc}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = self.session.get(embed_url, headers=headers, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] FileMoon sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            title = None
            if soup and soup.title:
                title = soup.title.get_text(strip=True).split("-")[0].strip()
            if not title:
                m_t = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_t:
                    title = m_t.group(1).split("-")[0].strip()

            # Packed JS'i çöz
            packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?\}\('.+?\.split\('\|'\)\)", html)
            if not packed_match:
                packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?\}\(\".+?\.split\(\"\|\"\)\)", html)

            direct_url = None
            if packed_match:
                unpacked = unpack_js(packed_match.group(0))
                # sources: [{file: "..."}] ara
                src_match = re.search(r'sources\s*:\s*\[\s*\{\s*file\s*:\s*["\']([^"\']+)["\']', unpacked)
                if not src_match:
                    src_match = re.search(r'file\s*:\s*["\'](https?://[^"\']+\.(?:mp4|m3u8|mkv)[^"\']*)["\']', unpacked)

                if src_match:
                    direct_url = src_match.group(1)

            # Fallback
            if not direct_url:
                m = re.search(r'["\'](https?://[^"\']+\.(?:mp4|m3u8)[^"\']*)["\']', html)
                if m:
                    direct_url = m.group(1)

            if not direct_url:
                self.log("[!] FileMoon video akışı bulunamadı.")
                return []

            filename = sanitize_filename(title or "filemoon_video.mp4")
            if not filename.endswith((".mp4", ".mkv", ".m3u8", ".ts")):
                filename += ".mp4"

            self.log(f"[✓] FileMoon Medyası Hazır: {filename}")
            return [{
                "name": filename,
                "url": direct_url,
                "size": 0,
                "subfolder": "FileMoon",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": embed_url
                }
            }]

        except Exception as e:
            self.log(f"[!] FileMoon hatası: {e}")
            return []
