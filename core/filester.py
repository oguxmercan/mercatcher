#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Filester Çıkarıcı (Extractor)
filester.me ve filester.net üzerindeki klasörleri ve tekil dosyaları çeker.
"""

import os
import re
import urllib.parse
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename

class FilesterExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_filester_url(self, url: str) -> bool:
        return "filester." in url

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": base_origin
        }

        # 1. Klasör Bağlantısı mı? (/f/ID)
        if "/f/" in url:
            return self.extract_folder(url, base_origin, headers)

        # 2. Tekil Dosya Bağlantısı mı?
        return self.extract_single_file(url, base_origin, headers)

    def extract_folder(self, folder_url: str, base_origin: str, headers: dict) -> list:
        self.log(f"[*] Filester klasörü taranıyor: {folder_url}")
        all_items = []
        page = 1

        try:
            folder_title = "Filester_Folder"
            while True:
                curr_url = folder_url if page == 1 else f"{folder_url}?page={page}"
                resp = self.session.get(curr_url, headers=headers, timeout=25)
                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "html.parser") if BeautifulSoup else None
                if page == 1:
                    if soup and soup.title:
                        folder_title = sanitize_filename(soup.title.get_text(strip=True).split("-")[0].strip())
                    else:
                        m_t = re.search(r'<title>(.*?)</title>', resp.text, re.I)
                        if m_t:
                            folder_title = sanitize_filename(m_t.group(1).split("-")[0].strip())

                # Dosya bağlantılarını topla
                file_links = []
                if soup:
                    for a in soup.find_all("a", href=True):
                        h = a["href"]
                        if "/d/" in h or "/file/" in h or "/download/" in h:
                            full = urllib.parse.urljoin(base_origin, h)
                            if full not in file_links and full != curr_url:
                                file_links.append(full)
                else:
                    for m_h in re.finditer(r'href=["\']([^"\']*(?:/d/|/file/|/download/)[^"\']*)["\']', resp.text):
                        full = urllib.parse.urljoin(base_origin, m_h.group(1))
                        if full not in file_links and full != curr_url:
                            file_links.append(full)

                if not file_links:
                    break

                for flk in file_links:
                    items = self.extract_single_file(flk, base_origin, headers, subfolder=folder_title)
                    all_items.extend(items)

                # Sonraki sayfa var mı kontrol et
                has_next = False
                if soup:
                    next_page = soup.find("a", href=re.compile(rf"page={page+1}"))
                    if next_page:
                        has_next = True
                elif f"page={page+1}" in resp.text:
                    has_next = True

                if not has_next:
                    break
                page += 1

            self.log(f"[✓] Filester klasöründen toplam {len(all_items)} dosya bulundu.")
            return all_items

        except Exception as e:
            self.log(f"[!] Filester klasör hatası: {e}")
            return all_items

    def extract_single_file(self, file_url: str, base_origin: str, headers: dict, subfolder="Filester") -> list:
        try:
            resp = self.session.get(file_url, headers=headers, timeout=25)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser") if BeautifulSoup else None
            filename = None
            if soup and soup.title:
                filename = soup.title.get_text(strip=True).split("-")[0].strip()
            if not filename:
                m_t = re.search(r'<title>(.*?)</title>', resp.text, re.I)
                if m_t:
                    filename = m_t.group(1).split("-")[0].strip()

            direct_url = None
            # Download butonu veya direct link
            if soup:
                dl_btn = soup.find("a", href=re.compile(r"/download/|/get/|\.mp4|\.mkv|\.zip|\.rar", re.I))
                if dl_btn:
                    direct_url = dl_btn.get("href")

            if not direct_url:
                m_dl = re.search(r'href=["\']([^"\']*(?:/download/|/get/|\.(?:mp4|mkv|zip|rar))[^"\']*)["\']', resp.text, re.I)
                if m_dl:
                    direct_url = m_dl.group(1)

            if not direct_url and soup:
                vid = soup.find("source", src=True) or soup.find("video", src=True)
                if vid:
                    direct_url = vid.get("src")

            if not direct_url:
                m_vid = re.search(r'<(?:source|video)[^>]+src=["\']([^"\']+)["\']', resp.text, re.I)
                if m_vid:
                    direct_url = m_vid.group(1)

            if not direct_url:
                # Buton / link form
                form = soup.find("form", action=re.compile(r"download"))
                if form and form.get("action"):
                    direct_url = form.get("action")

            if direct_url:
                if direct_url.startswith("/"):
                    direct_url = urllib.parse.urljoin(base_origin, direct_url)

                fname = sanitize_filename(filename or os.path.basename(urllib.parse.urlparse(direct_url).path) or f"filester_file")
                return [{
                    "name": fname,
                    "url": direct_url,
                    "size": 0,
                    "subfolder": subfolder,
                    "headers": {
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": file_url
                    }
                }]

        except Exception as e:
            self.log(f"[!] Filester dosya çıkarma hatası: {e}")

        return []
