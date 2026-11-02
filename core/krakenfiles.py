#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - KrakenFiles Çıkarıcı (Extractor)
KrakenFiles indirme bağlantılarını ve tokenlerini çözümler.
"""

import re
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename

class KrakenFilesExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_kraken_url(self, url: str) -> bool:
        return "krakenfiles.com" in url

    def extract(self, url: str) -> list:
        url = url.strip()
        hash_match = re.search(r"krakenfiles\.com/(?:view/)?([a-zA-Z0-9]+)", url)
        if not hash_match:
            self.log("[!] Geçersiz KrakenFiles bağlantısı.")
            return []

        file_hash = hash_match.group(1)
        page_url = f"https://krakenfiles.com/view/{file_hash}/file.html"

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://krakenfiles.com/"
        }

        try:
            self.log(f"[*] KrakenFiles sayfası inceleniyor: {page_url}")
            resp = self.session.get(page_url, headers=headers, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] KrakenFiles sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            # 1. Dosya Adını Çek
            filename = None
            if soup:
                title_tag = soup.find("h5", class_="nk-iv-wg4-title") or soup.find("div", class_="coin-name")
                if title_tag:
                    filename = title_tag.get_text(strip=True)
                if not filename:
                    name_tag = soup.find("div", class_="nk-file-name") or soup.find("span", class_="name")
                    if name_tag:
                        filename = name_tag.get_text(strip=True)
                if not filename and soup.title:
                    filename = soup.title.get_text(strip=True).split("-")[0].strip()

            if not filename:
                m_title = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_title:
                    filename = m_title.group(1).split("-")[0].strip()

            filename = sanitize_filename(filename or f"kraken_{file_hash}")

            # 2. Token ve İndirme Hash'ini Çek
            token = None
            token_input = soup.find("input", id="dl-token") or soup.find("input", attrs={"name": "token"})
            if token_input:
                token = token_input.get("value")
            else:
                m = re.search(r'id=["\']dl-token["\'][^>]*value=["\']([^"\']+)["\']', html)
                if m:
                    token = m.group(1)

            if not token:
                self.log("[!] KrakenFiles indirme tokenı bulunamadı.")
                return []

            # 3. Download API'sine istek yap
            dl_api = f"https://krakenfiles.com/download/{file_hash}"
            post_headers = {
                "User-Agent": DEFAULT_USER_AGENT,
                "Referer": page_url,
                "Origin": "https://krakenfiles.com",
                "X-Requested-With": "XMLHttpRequest"
            }

            dl_resp = self.session.post(dl_api, data={"token": token}, headers=post_headers, timeout=25)
            if dl_resp.status_code != 200:
                self.log(f"[!] KrakenFiles indirme linki alınamadı (HTTP {dl_resp.status_code})")
                return []

            direct_url = None
            try:
                data = dl_resp.json()
                direct_url = data.get("url")
            except Exception:
                if "http" in dl_resp.text:
                    direct_url = dl_resp.text.strip()

            if not direct_url:
                self.log("[!] KrakenFiles doğrudan indirme adresi boş döndü.")
                return []

            self.log(f"[✓] KrakenFiles Dosyası Hazır: {filename}")
            return [{
                "name": filename,
                "url": direct_url,
                "size": 0,
                "subfolder": "KrakenFiles",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": page_url
                }
            }]

        except Exception as e:
            self.log(f"[!] KrakenFiles hatası: {e}")
            return []
