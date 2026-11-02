#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - DoodStream Çıkarıcı (Extractor)
doodstream.com, dood.to, dood.so, dood.cx, ds2play.com vb. servislerden video indirir.
"""

import re
import time
import random
import string
import urllib.parse
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename

class DoodStreamExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_dood_url(self, url: str) -> bool:
        return any(d in url for d in [
            "doodstream.com", "dood.to", "dood.so", "dood.cx", "dood.watch",
            "dood.pm", "dood.wf", "dood.re", "ds2play.com", "doods.pro", "dood.ws"
        ])

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc

        # /d/ bağlantısını /e/ embed formatına dönüştür
        embed_url = re.sub(r"/(?:d|f)/([a-zA-Z0-9]+)", r"/e/\1", url)
        if not embed_url.startswith("http"):
            embed_url = f"https://{netloc}{embed_url}"

        self.log(f"[*] DoodStream taranıyor: {embed_url}")
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": f"https://{netloc}/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = self.session.get(embed_url, headers=headers, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] DoodStream sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            # Başlık
            title = None
            if soup and soup.title:
                title = soup.title.get_text(strip=True)
            if not title:
                m_t = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_t:
                    title = m_t.group(1).strip()
            if title:
                title = re.sub(r"(?:Watch\s*)?[-–|]?\s*DoodStream.*$", "", title, flags=re.I).strip()

            # pass_md5 yolunu bul
            md5_match = re.search(r"['\"](/pass_md5/[a-zA-Z0-9\-_/]+)['\"]", html)
            if not md5_match:
                self.log("[!] DoodStream pass_md5 anahtarı bulunamadı.")
                return []

            md5_path = md5_match.group(1)
            pass_url = f"https://{netloc}{md5_path}"

            # pass_md5 isteği gönder
            md5_resp = self.session.get(pass_url, headers={"User-Agent": DEFAULT_USER_AGENT, "Referer": embed_url}, timeout=20)
            if md5_resp.status_code != 200:
                self.log(f"[!] DoodStream pass_md5 yanıt vermedi (HTTP {md5_resp.status_code})")
                return []

            base_stream = md5_resp.text.strip()
            if not base_stream.startswith("http"):
                self.log(f"[!] DoodStream akış linki çözülemedi: {base_stream}")
                return []

            # Rastgele token & timestamp oluştur (DoodStream protokol kuralı)
            rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            token = md5_path.split("/")[-1]
            expiry = int(time.time() * 1000)

            direct_url = f"{base_stream}{rand_str}?token={token}&expiry={expiry}"
            filename = sanitize_filename(title or f"doodstream_{token}.mp4")
            if not filename.endswith((".mp4", ".mkv", ".webm")):
                filename += ".mp4"

            self.log(f"[✓] DoodStream Medyası Hazır: {filename}")
            return [{
                "name": filename,
                "url": direct_url,
                "size": 0,
                "subfolder": "DoodStream",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": embed_url
                }
            }]

        except Exception as e:
            self.log(f"[!] DoodStream hatası: {e}")
            return []
