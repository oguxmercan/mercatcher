#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Gofile.io Çözümleyici Modülü
"""

import os
import re
import requests
from .config import DEFAULT_USER_AGENT, DEFAULT_LANG
from .utils import sanitize_filename, load_gofile_token, save_gofile_token, calculate_website_token

class GofileExtractor:
    BASE_API = "https://api.gofile.io"

    def __init__(self, session: requests.Session, token: str = None, log_func=None):
        self.session = session
        self.log_func = log_func or print
        self.token = token.strip() if token else load_gofile_token()

    def log(self, msg: str):
        self.log_func(msg)

    def get_token(self) -> str:
        """Gofile API için misafir veya mevcut token alır."""
        if self.token:
            return self.token

        try:
            url = f"{self.BASE_API}/accounts"
            headers = {"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"}
            res = self.session.post(url, headers=headers, timeout=15)
            data = res.json()
            if data.get("status") == "ok":
                self.token = data.get("data", {}).get("token", "")
                if self.token:
                    save_gofile_token(self.token)
                    self.log("[*] Gofile misafir oturumu oluşturuldu ve kaydedildi.")
                    return self.token
            elif data.get("status") == "error-rateLimit":
                self.log("[!] Gofile Misafir Hesabı Sınırı (Rate Limit): Yeni misafir hesabı oluşturulamadı. Lütfen 'https://gofile.io/myprofile' adresinden ücretsiz hesap açıp tokeninizi arayüzdeki alana yapıştırın.")
            else:
                self.log(f"[!] Gofile oturum hatası: {data.get('status')}")
        except Exception as e:
            self.log(f"[!] Gofile token alma bağlantı hatası: {e}")
        return ""

    def parse_content_id(self, url: str) -> str:
        """https://gofile.io/d/XXXXXX linkinden content ID çıkarır."""
        match = re.search(r"gofile\.io/d/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)
        return ""

    def fetch_folder_items(self, content_id: str, subfolder_path: str = "") -> list:
        """Belirtilen folder ID altındaki tüm dosya ve alt klasörleri çeker."""
        items = []
        token = self.get_token()

        if not token:
            self.log("[!] Gofile tokeni bulunamadığı için içerik sorgulanamadı.")
            return items

        wt = calculate_website_token(DEFAULT_USER_AGENT, DEFAULT_LANG, token)

        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Website-Token": wt,
            "X-BL": DEFAULT_LANG,
            "Cookie": f"accountToken={token}"
        }

        url = f"{self.BASE_API}/contents/{content_id}?page=1&pageSize=1000"
        try:
            res = self.session.get(url, headers=headers, timeout=25)
            try:
                data = res.json()
            except Exception:
                self.log(f"[!] Gofile geçersiz yanıt döndürdü (HTTP {res.status_code})")
                return items

            status_str = data.get("status")

            if status_str != "ok":
                if status_str == "error-rateLimit":
                    self.log(f"[!] Gofile İstek Sınırı ({content_id}): Gofile IP kotası uyguladı. Lütfen bekleyin veya ayarlardan hesap tokeninizi girin.")
                elif status_str == "error-notFound":
                    self.log(f"[!] Gofile ({content_id}): İçerik bulunamadı veya silinmiş.")
                elif status_str == "error-notPremium":
                    self.log(f"[!] Gofile ({content_id}): Bu klasör Premium hesap gerektiriyor veya erişimi kısıtlı.")
                elif status_str == "error-password":
                    self.log(f"[!] Gofile ({content_id}): Bu klasör şifre korumalı.")
                elif status_str in ["error-token", "error-wrongToken", "error-accountId"]:
                    self.log("[!] Gofile: Token geçersiz. Sıfırlanıyor...")
                    save_gofile_token("")
                    self.token = ""
                else:
                    self.log(f"[!] Gofile API hatası ({content_id}): {status_str}")
                return items

            folder_data = data.get("data", {})
            folder_name = sanitize_filename(folder_data.get("name") or content_id)
            current_path = os.path.join(subfolder_path, folder_name) if subfolder_path else folder_name

            raw_children = folder_data.get("children", {})
            if isinstance(raw_children, dict):
                children_list = list(raw_children.values())
            elif isinstance(raw_children, list):
                children_list = raw_children
            else:
                children_list = []

            for child in children_list:
                c_type = child.get("type")
                if c_type == "folder":
                    child_id = child.get("id")
                    items.extend(self.fetch_folder_items(child_id, current_path))
                elif c_type == "file":
                    file_name = sanitize_filename(child.get("name") or child.get("id"))
                    file_url = child.get("link")
                    size = child.get("size", 0)
                    if file_url:
                        items.append({
                            "name": file_name,
                            "url": file_url,
                            "size": size,
                            "subfolder": current_path,
                            "headers": {
                                "Authorization": f"Bearer {token}",
                                "Cookie": f"accountToken={token}",
                                "User-Agent": DEFAULT_USER_AGENT
                            }
                        })

            if items:
                self.log(f"[✓] Gofile: '{folder_name}' klasöründe {len(items)} dosya bulundu.")
            else:
                self.log(f"[*] Gofile: '{folder_name}' klasörü boş veya dosya içermiyor.")

        except Exception as e:
            self.log(f"[!] Gofile veri çekme hatası ({content_id}): {e}")

        return items
