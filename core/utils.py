#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Yardımcı Araçlar ve Token Yönetimi
"""

import os
import re
import time
import json
import hashlib
import urllib.parse
from .config import TOKEN_FILE, GOFILE_SALT

def sanitize_filename(name: str) -> str:
    """Dosya adlarındaki geçersiz karakterleri temizler."""
    if not name:
        return "unnamed_file"
    name = urllib.parse.unquote(name)
    name = re.sub(r'[\\/*?:"<>|]', "_", name)
    return name.strip(". ")

def load_gofile_token() -> str:
    """Kayıtlı Gofile tokenini okur."""
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                return d.get("token", "").strip()
        except Exception:
            pass
    return ""

def save_gofile_token(token: str):
    """Gofile tokenini dosyaya kaydeder."""
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump({"token": token.strip()}, f)
    except Exception:
        pass

def calculate_website_token(user_agent: str, language: str, account_token: str, salt: str = GOFILE_SALT) -> str:
    """
    Gofile X-Website-Token (WT) hash hesaplayıcı.
    Formül: sha256(UA + '::' + LANG + '::' + TOKEN + '::' + TIME_BUCKET + '::' + SALT)
    """
    time_bucket = str(int(time.time() // 14400))  # 4 saatlik zaman penceresi
    raw = f"{user_agent}::{language}::{account_token}::{time_bucket}::{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
