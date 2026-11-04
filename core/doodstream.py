#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - DoodStream & Mirror Çıkarıcı (Extractor)
doodstream.com, dood.to, ds2play.com, playmogo.com vb. servislerden video indirir.
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
from .config import DEFAULT_USER_AGENT, DOODSTREAM_DOMAINS
from .utils import sanitize_filename

class DoodStreamExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_dood_url(self, url: str) -> bool:
        url_lower = url.lower()
        parsed = urllib.parse.urlparse(url_lower)
        netloc = parsed.netloc
        if any(d in netloc for d in DOODSTREAM_DOMAINS):
            return True
        if "dood" in netloc or "ds2play" in netloc or "ds2video" in netloc or "playmogo" in netloc:
            return True
        return False

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc

        # /d/, /f/, /w/, /v/ veya doğrudan ID'yi /e/ embed formatına dönüştür
        m_id = re.search(r"/(?:e|d|f|w|v)/([a-zA-Z0-9]+)", parsed.path)
        if not m_id:
            m_id = re.search(r"/([a-zA-Z0-9]{8,})", parsed.path)

        if m_id:
            video_id = m_id.group(1)
            embed_url = f"https://{netloc}/e/{video_id}"
        else:
            embed_url = re.sub(r"/(?:d|f|w|v)/([a-zA-Z0-9]+)", r"/e/\1", url)
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
            effective_netloc = urllib.parse.urlparse(resp.url).netloc or netloc

            # Başlık tespiti
            title = None
            if BeautifulSoup:
                try:
                    soup = BeautifulSoup(html, "html.parser")
                    if soup and soup.title:
                        title = soup.title.get_text(strip=True)
                except Exception:
                    pass
            if not title:
                m_t = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_t:
                    title = m_t.group(1).strip()
            if title:
                title = re.sub(r"(?:Watch\s*)?[-–|]?\s*(?:DoodStream|Dood|Playmogo).*$", "", title, flags=re.I).strip()

            # pass_md5 yolunu bul
            md5_match = re.search(r"['\"](/pass_md5/[a-zA-Z0-9\-_/]+)['\"]", html)
            if not md5_match:
                self.log("[!] DoodStream pass_md5 anahtarı bulunamadı.")
                return []

            md5_path = md5_match.group(1)
            pass_url = f"https://{effective_netloc}{md5_path}"

            # pass_md5 isteği gönder
            md5_headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": resp.url
            }
            md5_resp = self.session.get(pass_url, headers=md5_headers, timeout=20)
            if md5_resp.status_code != 200:
                self.log(f"[!] DoodStream pass_md5 yanıt vermedi (HTTP {md5_resp.status_code})")
                return []

            base_stream = md5_resp.text.strip()
            if base_stream == "RELOAD":
                time.sleep(1)
                md5_resp = self.session.get(pass_url, headers=md5_headers, timeout=20)
                base_stream = md5_resp.text.strip()

            if not base_stream.startswith("http"):
                self.log(f"[!] DoodStream akış linki çözülemedi: {base_stream}")
                return []

            # Tokeni makePlay() fonksiyonundan veya md5_path'ten çıkar
            token_match = re.search(r"\?token=([a-zA-Z0-9]+)", html)
            token = token_match.group(1) if token_match else md5_path.split("/")[-1]

            # Rastgele karakter ve timestamp oluştur (DoodStream protokol kuralı)
            rand_str = "".join(random.choices(string.ascii_letters + string.digits, k=10))
            expiry = int(time.time() * 1000)

            direct_url = f"{base_stream}{rand_str}?token={token}&expiry={expiry}"
            filename = sanitize_filename(title or f"doodstream_{token}.mp4")
            if not filename.endswith((".mp4", ".mkv", ".webm")):
                filename += ".mp4"

            # Dosya boyutunu hızlı HEAD ile öğren
            size = 0
            try:
                head_resp = self.session.head(
                    direct_url, 
                    headers={"User-Agent": DEFAULT_USER_AGENT, "Referer": resp.url}, 
                    timeout=6, 
                    allow_redirects=True
                )
                if head_resp.status_code == 200:
                    size = int(head_resp.headers.get("Content-Length", 0))
            except Exception:
                size = 0

            self.log(f"[✓] DoodStream Medyası Hazır: {filename} ({round(size/(1024*1024), 1)} MB)" if size else f"[✓] DoodStream Medyası Hazır: {filename}")
            return [{
                "name": filename,
                "url": direct_url,
                "size": size,
                "subfolder": "DoodStream",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": resp.url
                }
            }]

        except Exception as e:
            self.log(f"[!] DoodStream hatası: {e}")
            return []
