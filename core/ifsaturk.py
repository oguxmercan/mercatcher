#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - İfsaTürk Çıkarıcı (Extractor)
ifsaturkk.com ve benzeri servislerden fotoğraf albümlerini ve videoları toplu olarak indirir.
"""

import re
import urllib.parse
import requests
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .config import DEFAULT_USER_AGENT, IFSATURK_DOMAINS
from .utils import sanitize_filename

class IfsaTurkExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_ifsaturk_url(self, url: str) -> bool:
        url_lower = url.lower()
        parsed = urllib.parse.urlparse(url_lower)
        netloc = parsed.netloc
        if any(d in netloc for d in IFSATURK_DOMAINS):
            return True
        return "ifsaturk" in netloc

    def extract(self, url: str) -> list:
        url = url.strip()
        parsed = urllib.parse.urlparse(url)
        path = parsed.path.lower()

        # Tekil video sayfası kontrolü
        if "/video/" in path:
            return self.extract_single_video(url)
        
        # Albüm / galeri veya genel sayfa kontrolü
        return self.extract_gallery(url)

    def extract_gallery(self, start_url: str) -> list:
        parsed = urllib.parse.urlparse(start_url)
        netloc = parsed.netloc
        base_origin = f"{parsed.scheme}://{netloc}"

        # Albüm slug tespiti (örn: fairyfreak)
        clean_path = parsed.path.rstrip("/")
        path_parts = [p for p in clean_path.split("/") if p]
        album_slug = path_parts[-1] if path_parts else "gallery"

        self.log(f"[*] İfsaTürk albümü taranıyor: {start_url}")
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": base_origin + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        visited_pages = set()
        to_visit = [start_url]
        found_media = []
        seen_urls = set()
        album_name = None

        while to_visit:
            curr_url = to_visit.pop(0)
            if curr_url in visited_pages:
                continue
            visited_pages.add(curr_url)

            if len(visited_pages) > 1:
                self.log(f"[*] Sayfa taranıyor: {curr_url}")

            try:
                resp = self.session.get(curr_url, headers=headers, timeout=20)
                if resp.status_code != 200:
                    continue
            except Exception as e:
                self.log(f"[!] Sayfa isteği başarısız: {e}")
                continue

            html = resp.text

            # Albüm başlığını ilk sayfadan al
            if not album_name:
                soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
                h1 = soup.find("h1") if soup else None
                title = h1.get_text(strip=True) if h1 else None
                if not title and soup and soup.title:
                    title = soup.title.get_text(strip=True)
                if not title:
                    m_t = re.search(r'<title>(.*?)</title>', html, re.I)
                    if m_t:
                        title = m_t.group(1).strip()
                
                if title:
                    # Temizleme
                    title = re.sub(r"\s*[-–|·]\s*İfsa\s*Türk.*$", "", title, flags=re.I).strip()
                    title = re.sub(r"\s*fotoğrafları\s*$", "", title, flags=re.I).strip()
                
                album_name = sanitize_filename(title or album_slug)

            # 1. /uploads/ altındaki medya dosyalarını topla
            upload_matches = re.findall(
                r'(/uploads/[a-zA-Z0-9\-_.]+\.(?:jpg|jpeg|png|webp|gif|mp4|webm))', 
                html, 
                re.I
            )
            for m in upload_matches:
                full_m = urllib.parse.urljoin(base_origin, m)
                if full_m not in seen_urls:
                    seen_urls.add(full_m)
                    found_media.append((full_m, "upload"))

            # 2. Sayfada gömülü BunnyCDN videoları varsa tespit et
            bcdn_matches = re.findall(r'https?://[^\s"\'<>]+\.b-cdn\.net/[^\s"\'<>]*playlist\.m3u8[^\s"\'<>]*', html)
            for bm in bcdn_matches:
                clean_pl = bm.replace('\\u0026', '&').rstrip('\\"')
                if clean_pl not in seen_urls:
                    seen_urls.add(clean_pl)
                    resolved_v = self._resolve_bunnycdn_mp4(clean_pl, base_origin)
                    if resolved_v:
                        found_media.append((resolved_v, "video"))

            # 3. Sayfalama (Pagination) bağlantılarını bul
            soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None
            if soup:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if "page=" in href and (album_slug in href or parsed.path in href):
                        full_page = urllib.parse.urljoin(start_url, href)
                        if full_page not in visited_pages and full_page not in to_visit:
                            to_visit.append(full_page)
            else:
                for href in re.findall(r'href=["\']([^"\']*page=\d+[^"\']*)["\']', html):
                    if album_slug in href or parsed.path in href:
                        full_page = urllib.parse.urljoin(start_url, href)
                        if full_page not in visited_pages and full_page not in to_visit:
                            to_visit.append(full_page)

        if not found_media:
            self.log("[!] İfsaTürk albümünde indirilebilir medya bulunamadı.")
            return []

        album_title = album_name or sanitize_filename(album_slug)
        subfolder_name = f"IfsaTurk/{album_title}"
        self.log(f"[✓] {len(found_media)} medya dosyası bulundu ({album_title})")

        items = []
        for idx, (m_url, m_type) in enumerate(found_media, 1):
            parsed_media = urllib.parse.urlparse(m_url)
            orig_fname = parsed_media.path.split("/")[-1]
            ext = "." + orig_fname.split(".")[-1] if "." in orig_fname else (".mp4" if m_type == "video" else ".jpg")
            clean_base = sanitize_filename(orig_fname)
            
            # Format: AlbumAdi_001_dosya.jpg
            fname = f"{album_title}_{idx:03d}_{clean_base}"
            if not fname.lower().endswith(ext.lower()):
                fname += ext

            items.append({
                "name": fname,
                "url": m_url,
                "size": 0,
                "subfolder": subfolder_name,
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": base_origin + "/"
                }
            })

        return items

    def extract_single_video(self, url: str) -> list:
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        base_origin = f"{parsed.scheme}://{netloc}"

        self.log(f"[*] İfsaTürk video sayfası taranıyor: {url}")
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": base_origin + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            resp = self.session.get(url, headers=headers, timeout=20)
            if resp.status_code != 200:
                self.log(f"[!] Video sayfasına ulaşılamadı (HTTP {resp.status_code})")
                return []
        except Exception as e:
            self.log(f"[!] Video sayfası isteği başarısız: {e}")
            return []

        html = resp.text
        soup = BeautifulSoup(html, "html.parser") if BeautifulSoup else None

        # Başlık
        h1 = soup.find("h1") if soup else None
        title = h1.get_text(strip=True) if h1 else None
        if not title and soup and soup.title:
            title = soup.title.get_text(strip=True)
        if not title:
            m_t = re.search(r'<title>(.*?)</title>', html, re.I)
            if m_t:
                title = m_t.group(1).strip()
        
        if title:
            title = re.sub(r"\s*[-–|·]\s*İfsa\s*Türk.*$", "", title, flags=re.I).strip()
        
        video_title = sanitize_filename(title or "video")

        # 1. BunnyCDN playlist tespit et
        m3u8_matches = re.findall(r'https?://[^\s"\'<>]+\.b-cdn\.net/[^\s"\'<>]*playlist\.m3u8[^\s"\'<>]*', html)
        tokened = [m.replace('\\u0026', '&').rstrip('\\"') for m in m3u8_matches if "token=" in m]
        if not tokened and m3u8_matches:
            tokened = [m.replace('\\u0026', '&').rstrip('\\"') for m in m3u8_matches]

        if tokened:
            pl_url = tokened[0]
            resolved_v, size = self._resolve_bunnycdn_mp4_with_size(pl_url, base_origin)
            if resolved_v:
                fname = f"{video_title}.mp4"
                self.log(f"[✓] İfsaTürk Videosu Hazır: {fname} ({round(size/(1024*1024), 1)} MB)" if size else f"[✓] İfsaTürk Videosu Hazır: {fname}")
                return [{
                    "name": fname,
                    "url": resolved_v,
                    "size": size,
                    "subfolder": "IfsaTurk/Videos",
                    "headers": {
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Referer": base_origin + "/"
                    }
                }]

        # 2. Doğrudan video tagı veya /uploads/ mp4 var mı?
        direct_mp4 = re.findall(r'(/uploads/[a-zA-Z0-9\-_.]+\.(?:mp4|webm))', html, re.I)
        if direct_mp4:
            v_url = urllib.parse.urljoin(base_origin, direct_mp4[0])
            fname = f"{video_title}.mp4"
            self.log(f"[✓] İfsaTürk Doğrudan Videosu Hazır: {fname}")
            return [{
                "name": fname,
                "url": v_url,
                "size": 0,
                "subfolder": "IfsaTurk/Videos",
                "headers": {
                    "User-Agent": DEFAULT_USER_AGENT,
                    "Referer": base_origin + "/"
                }
            }]

        self.log("[!] İfsaTürk videosu çözümlenemedi.")
        return []

    def _resolve_bunnycdn_mp4(self, playlist_url: str, referer: str) -> str:
        url, _ = self._resolve_bunnycdn_mp4_with_size(playlist_url, referer)
        return url

    def _resolve_bunnycdn_mp4_with_size(self, playlist_url: str, referer: str) -> tuple:
        parsed = urllib.parse.urlparse(playlist_url)
        base_dir = parsed.path.rsplit("/", 1)[0]
        query = f"?{parsed.query}" if parsed.query else ""
        headers = {"User-Agent": DEFAULT_USER_AGENT, "Referer": referer}

        # Öncelikli kalite adayları
        candidates = ["original", "play_1080p.mp4", "play_720p.mp4", "play_480p.mp4"]
        for c in candidates:
            test_url = f"{parsed.scheme}://{parsed.netloc}{base_dir}/{c}{query}"
            try:
                h = self.session.head(test_url, headers=headers, timeout=5, allow_redirects=True)
                if h.status_code == 200:
                    size = int(h.headers.get("Content-Length", 0))
                    return test_url, size
            except Exception:
                pass

        return playlist_url, 0
