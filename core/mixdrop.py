#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - MixDrop Çıkarıcı (Extractor)
mixdrop.co, mixdrop.to, mixdrop.sx vb. aynalardan video/dosya linklerini çözer.
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

class MixDropExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_mixdrop_url(self, url: str) -> bool:
        return any(d in url for d in [
            "mixdrop.co", "mixdrop.to", "mixdrop.sx", "mixdrop.bz", 
            "mixdrop.ch", "mixdrop.ag", "mixdrop.gl", "mixdrop.club"
        ])

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc

        # /f/ bağlantısını embed /e/ bağlantısına çevir (Daha temiz çözülür)
        embed_url = re.sub(r"/f/([a-zA-Z0-9]+)", r"/e/\1", url)
        if not embed_url.startswith("http"):
            embed_url = f"https://{netloc}{embed_url}"

        self.log(f"[*] MixDrop inceleniyor: {embed_url}")
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": f"https://{netloc}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = self.session.get(embed_url, headers=headers, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] MixDrop sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            # Dosya başlığı
            title = None
            if soup:
                title_tag = soup.find("span", class_="title") or soup.find("div", class_="title")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                if not title and soup.title:
                    title = soup.title.get_text(strip=True).split("-")[0].strip()
            if not title:
                m_t = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_t:
                    title = m_t.group(1).split("-")[0].strip()

            # Packed JS ara
            packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?\}\('.+?\.split\('\|'\)\)", html)
            if not packed_match:
                packed_match = re.search(r"eval\(function\(p,a,c,k,e,d\).+?\}\(\".+?\.split\(\"\|\"\)\)", html)

            direct_url = None
            if packed_match:
                unpacked = unpack_js(packed_match.group(0))
                # MDCore.wurl veya vsrc bul
                wurl_match = re.search(r'MDCore\.(?:wurl|vsrc)\s*=\s*["\']([^"\']+)["\']', unpacked)
                if not wurl_match:
                    wurl_match = re.search(r'(?:wurl|vsrc)\s*=\s*["\']([^"\']+)["\']', unpacked)
                if not wurl_match:
                    wurl_match = re.search(r'["\'](//[^"\']+\.(?:mp4|mkv|mov|webm)[^"\']*)["\']', unpacked)

                if wurl_match:
                    direct_url = wurl_match.group(1)

            # Fallback direct link
            if not direct_url:
                m = re.search(r'["\'](https?://[^"\']+\.delivery\.mixdrop\.[^"\']+)["\']', html)
                if m:
                    direct_url = m.group(1)

            if not direct_url:
                self.log("[!] MixDrop video/medya URL'si çözümlenemedi.")
                return []

            if direct_url.startswith("//"):
                direct_url = "https:" + direct_url

            filename = sanitize_filename(title or "mixdrop_video.mp4")
            if not filename.endswith((".mp4", ".mkv", ".webm", ".avi", ".zip")):
                filename += ".mp4"

            self.log(f"[✓] MixDrop Medyası Hazır: {filename}")
            return [{
                "name": filename,
                "url": direct_url,
                "size": 0,
                "subfolder": "MixDrop",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": embed_url
                }
            }]

        except Exception as e:
            self.log(f"[!] MixDrop hatası: {e}")
            return []
