#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - CyberFile Çıkarıcı (Extractor)
cyberfile.me ve cyberfile.is servislerinden dosya ve klasörleri çeker.
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

class CyberFileExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_cyberfile_url(self, url: str) -> bool:
        return "cyberfile.me" in url or "cyberfile.is" in url

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        base_origin = f"{parsed.scheme}://{parsed.netloc}"

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": base_origin
        }

        self.log(f"[*] CyberFile bağlantısı taranıyor: {url}")
        try:
            resp = self.session.get(url, headers=headers, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] CyberFile sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []

            html = resp.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            # 1. Klasör mü kontrol et
            if "/folder/" in url or "/shared/" in url or "folder-content" in html:
                items = self._extract_folder_files(soup, html, base_origin, headers)
                if items:
                    self.log(f"[+] CyberFile Klasöründen {len(items)} dosya bulundu.")
                    return items

            # 2. Tekil Dosya İşlemi
            # Dosya adı
            filename = None
            if soup:
                title_tag = soup.find("h1", class_="file-title") or soup.find("div", class_="file-name")
                if title_tag:
                    filename = title_tag.get_text(strip=True)
                if not filename and soup.title:
                    filename = soup.title.get_text(strip=True).split("-")[0].strip()
            if not filename:
                m_title = re.search(r'<title>(.*?)</title>', html, re.I)
                if m_title:
                    filename = m_title.group(1).split("-")[0].strip()
            
            # Boyut
            size = 0
            size_match = re.search(r"(\d+(?:\.\d+)?)\s*(KB|MB|GB)", html, re.I)

            # Doğrudan İndirme Linki Arama
            direct_url = None

            # a) download_token içeren <a> veya buton
            if soup:
                token_link = soup.find("a", href=re.compile(r"download_token="))
                if token_link:
                    direct_url = token_link.get("href")
            if not direct_url:
                m_tok = re.search(r'href=["\']([^"\']*download_token=[^"\']*)["\']', html)
                if m_tok:
                    direct_url = m_tok.group(1)

            # b) /download/ içeren buton
            if not direct_url and soup:
                dl_link = soup.find("a", href=re.compile(r"/download/"))
                if dl_link:
                    direct_url = dl_link.get("href")
            if not direct_url:
                m_dl = re.search(r'href=["\']([^"\']*/download/[^"\']*)["\']', html)
                if m_dl:
                    direct_url = m_dl.group(1)

            # c) Medya oynatıcı içindeki video/source
            if not direct_url and soup:
                source = soup.find("source", src=True) or soup.find("video", src=True)
                if source:
                    direct_url = source.get("src")
            if not direct_url:
                m_src = re.search(r'<(?:source|video)[^>]+src=["\']([^"\']+)["\']', html, re.I)
                if m_src:
                    direct_url = m_src.group(1)

            # d) JS içi doğrudan linkler
            if not direct_url:
                m = re.search(r'["\'](https?://[^"\']+\?download_token=[^"\']+)["\']', html)
                if m:
                    direct_url = m.group(1)

            if direct_url:
                if direct_url.startswith("/"):
                    direct_url = urllib.parse.urljoin(base_origin, direct_url)

                fname = sanitize_filename(filename or os.path.basename(urllib.parse.urlparse(direct_url).path) or "cyberfile_download")
                self.log(f"[✓] CyberFile Dosyası Bulundu: {fname}")
                return [{
                    "name": fname,
                    "url": direct_url,
                    "size": size,
                    "subfolder": "CyberFile",
                    "headers": {
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": url
                    }
                }]

            self.log("[!] CyberFile indirme linki tespit edilemedi.")
            return []

        except Exception as e:
            self.log(f"[!] CyberFile hatası: {e}")
            return []

    def _extract_folder_files(self, soup, html: str, base_origin: str, headers: dict) -> list:
        links = []
        if soup:
            for a in soup.find_all("a", href=True):
                href = a.get("href")
                if re.match(r"^/[a-zA-Z0-9_-]{4,16}$", href) or "/file/" in href:
                    full_link = urllib.parse.urljoin(base_origin, href)
                    if full_link not in links:
                        links.append(full_link)
        else:
            for m in re.finditer(r'href=["\'](/file/[^"\']+|/[a-zA-Z0-9_-]{4,16})["\']', html):
                full_link = urllib.parse.urljoin(base_origin, m.group(1))
                if full_link not in links:
                    links.append(full_link)

        all_items = []
        for lk in links[:50]:  # Güvenlik sınırı
            res = self.extract(lk)
            all_items.extend(res)
        return all_items
