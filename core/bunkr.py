#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Bunkr Çözümleyici Modülü
"""

import os
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .config import DEFAULT_USER_AGENT, BUNKR_DOMAINS
from .utils import sanitize_filename

class BunkrExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log_func = log_func or print

    def log(self, msg: str):
        self.log_func(msg)

    def is_bunkr_url(self, url: str) -> bool:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return any(domain in netloc for domain in BUNKR_DOMAINS) or "balbums" in netloc

    def extract_album(self, album_url: str) -> list:
        """Bunkr ve Balbums albümünden tüm medya sayfalarını ve direkt linklerini toplar."""
        items = []
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": "https://google.com/"
        }
        try:
            res = self.session.get(album_url, headers=headers, timeout=20)
            if res.status_code != 200:
                self.log(f"[!] Bunkr/Balbums albümü açılamadı: HTTP {res.status_code}")
                return items

            html = res.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

            album_title = "Balbums_Album" if "balbums" in album_url.lower() else "Bunkr_Album"
            if soup:
                title_tag = soup.find("h1") or soup.find("title")
                if title_tag:
                    raw_title = title_tag.text
                    for sfx in ["- Bunkr", "- Balbums", "- balbums", "Balbums -", "Bunkr -"]:
                        raw_title = raw_title.replace(sfx, "")
                    album_title = sanitize_filename(raw_title.strip() or album_title)
            else:
                m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE)
                if m:
                    raw_title = re.sub(r"<[^>]+>", "", m.group(1))
                    for sfx in ["- Bunkr", "- Balbums", "- balbums", "Balbums -", "Bunkr -"]:
                        raw_title = raw_title.replace(sfx, "")
                    album_title = sanitize_filename(raw_title.strip() or album_title)

            media_page_urls = set()
            base_parsed = urllib.parse.urlparse(album_url)
            base_root = f"{base_parsed.scheme}://{base_parsed.netloc}"

            if soup:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if re.search(r"/(v|i|d)/[a-zA-Z0-9_-]+", href):
                        full_url = urllib.parse.urljoin(base_root, href)
                        media_page_urls.add(full_url)
                    elif re.search(r"\.(mp4|mkv|mov|webm|jpg|jpeg|png|webp|zip|rar)$", href, re.I):
                        direct_url = urllib.parse.urljoin(base_root, href)
                        fname = sanitize_filename(os.path.basename(urllib.parse.urlparse(direct_url).path))
                        items.append({
                            "name": fname,
                            "url": direct_url,
                            "size": 0,
                            "subfolder": album_title,
                            "headers": {"User-Agent": DEFAULT_USER_AGENT, "Referer": album_url}
                        })
            else:
                matches = re.findall(r'href=["\']([^"\']*(?:/(?:v|i|d)/[a-zA-Z0-9_-]+|\.(?:mp4|mkv|mov|webm|jpg|jpeg|png|webp|zip|rar)))["\']', html, re.I)
                for m in matches:
                    full_url = urllib.parse.urljoin(base_root, m)
                    if re.search(r"/(v|i|d)/[a-zA-Z0-9_-]+", full_url):
                        media_page_urls.add(full_url)
                    elif re.search(r"\.(mp4|mkv|mov|webm|jpg|jpeg|png|webp|zip|rar)$", full_url, re.I):
                        fname = sanitize_filename(os.path.basename(urllib.parse.urlparse(full_url).path))
                        items.append({
                            "name": fname,
                            "url": full_url,
                            "size": 0,
                            "subfolder": album_title,
                            "headers": {"User-Agent": DEFAULT_USER_AGENT, "Referer": album_url}
                        })

            self.log(f"[*] Albümde {len(media_page_urls)} medya sayfası bulundu. Taranıyor...")

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(self.extract_single_media, m_url, album_title): m_url for m_url in media_page_urls}
                for fut in as_completed(futures):
                    res_item = fut.result()
                    if res_item:
                        items.append(res_item)

        except Exception as e:
            self.log(f"[!] Bunkr albüm tarama hatası: {e}")

        return items

    def extract_single_media(self, page_url: str, album_name: str = "Bunkr_Media") -> dict:
        """Tek bir Bunkr sayfasını (/v/..., /i/...) açıp asıl dosya bağlantısını çeker."""
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": page_url
        }
        try:
            res = self.session.get(page_url, headers=headers, timeout=20)
            if res.status_code != 200:
                return None

            html = res.text
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
            direct_url = None
            filename = None

            if soup:
                dl_btn = soup.find("a", attrs={"download": True}) or soup.find("a", string=re.compile(r"Download", re.I))
                if dl_btn and dl_btn.get("href"):
                    direct_url = dl_btn["href"]
                    if dl_btn.get("download"):
                        filename = dl_btn["download"]

                if not direct_url:
                    vid = soup.find("video")
                    if vid:
                        src = vid.get("src") or (vid.find("source").get("src") if vid.find("source") else None)
                        if src:
                            direct_url = src

                if not direct_url:
                    img = soup.find("img", class_=re.compile(r"(media|content|image|full)", re.I))
                    if not img:
                        imgs = soup.find_all("img")
                        for i in imgs:
                            s = i.get("src", "")
                            if not re.search(r"(logo|icon|banner|favicon)", s, re.I):
                                direct_url = s
                                break
                    else:
                        direct_url = img.get("src")

            if not direct_url:
                v_match = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html)
                if v_match:
                    direct_url = v_match.group(1)

            if not direct_url:
                cdn_match = re.search(r'https?://[a-zA-Z0-9.-]+\.bunkr\.[a-z0-9]+/[^"\'\s<>]+', html)
                if cdn_match:
                    direct_url = cdn_match.group(0)

            if direct_url:
                direct_url = urllib.parse.urljoin(page_url, direct_url)

                if not filename:
                    parsed_path = urllib.parse.urlparse(direct_url).path
                    filename = os.path.basename(parsed_path) or f"media_{int(time.time()*1000)}"

                filename = sanitize_filename(filename)

                return {
                    "name": filename,
                    "url": direct_url,
                    "size": 0,
                    "subfolder": album_name,
                    "headers": {
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": page_url
                    }
                }
        except Exception as e:
            self.log(f"[!] Medya sayfası çözümlenemedi ({page_url}): {e}")

        return None
