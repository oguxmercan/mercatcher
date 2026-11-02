#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Pixeldrain Çıkarıcı (Extractor)
Hem tekil dosyaları (/u/ID) hem de albümleri/listeleri (/l/ID) destekler.
"""

import re
import requests
from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename

class PixeldrainExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_pixeldrain_url(self, url: str) -> bool:
        return "pixeldrain.com" in url

    def extract(self, url: str) -> list:
        url = url.strip()
        # 1. Albüm / Liste mi?
        list_match = re.search(r"pixeldrain\.com/l/([a-zA-Z0-9_-]+)", url)
        if list_match:
            list_id = list_match.group(1)
            return self.extract_list(list_id)

        # 2. Tekil Dosya mı?
        file_match = re.search(r"pixeldrain\.com/(?:u|api/file)/([a-zA-Z0-9_-]+)", url)
        if file_match:
            file_id = file_match.group(1)
            item = self.extract_file(file_id)
            return [item] if item else []

        self.log(f"[!] Tanınmayan Pixeldrain URL biçimi: {url}")
        return []

    def extract_file(self, file_id: str) -> dict:
        try:
            info_url = f"https://pixeldrain.com/api/file/{file_id}/info"
            res = self.session.get(info_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=20)
            if res.status_code == 200:
                data = res.json()
                name = sanitize_filename(data.get("name") or f"pixeldrain_{file_id}")
                size = data.get("size", 0)
                download_url = f"https://pixeldrain.com/api/file/{file_id}?download"
                self.log(f"[+] Pixeldrain Dosyası: {name} ({size} bayt)")
                return {
                    "name": name,
                    "url": download_url,
                    "size": size,
                    "subfolder": "Pixeldrain",
                    "headers": {"User-Agent": DEFAULT_USER_AGENT}
                }
            else:
                self.log(f"[!] Pixeldrain dosya bilgisi alınamadı (HTTP {res.status_code})")
        except Exception as e:
            self.log(f"[!] Pixeldrain hata: {e}")

        # Fallback
        return {
            "name": f"pixeldrain_{file_id}",
            "url": f"https://pixeldrain.com/api/file/{file_id}?download",
            "size": 0,
            "subfolder": "Pixeldrain",
            "headers": {"User-Agent": DEFAULT_USER_AGENT}
        }

    def extract_list(self, list_id: str) -> list:
        try:
            api_url = f"https://pixeldrain.com/api/list/{list_id}"
            res = self.session.get(api_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=25)
            if res.status_code != 200:
                self.log(f"[!] Pixeldrain liste okunamadı (HTTP {res.status_code})")
                return []

            data = res.json()
            title = sanitize_filename(data.get("title") or f"Pixeldrain_List_{list_id}")
            files = data.get("files", [])
            self.log(f"[+] Pixeldrain Albümü: '{title}' ({len(files)} dosya)")

            items = []
            for f in files:
                f_id = f.get("id")
                if not f_id:
                    continue
                f_name = sanitize_filename(f.get("name") or f"file_{f_id}")
                f_size = f.get("size", 0)
                items.append({
                    "name": f_name,
                    "url": f"https://pixeldrain.com/api/file/{f_id}?download",
                    "size": f_size,
                    "subfolder": title,
                    "headers": {"User-Agent": DEFAULT_USER_AGENT}
                })
            return items

        except Exception as e:
            self.log(f"[!] Pixeldrain liste alma hatası: {e}")
            return []
