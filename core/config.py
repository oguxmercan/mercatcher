#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Yapılandırma ve Sabitler
"""

import os

APP_NAME = "Mercatcher"
APP_TITLE = "Mercatcher - Bulk Media Downloader Pro"
APP_VERSION = "1.0.0"

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_LANG = "en-US"

# Gofile salt (X-Website-Token hesaplama)
GOFILE_SALT = "12af056dacea0b"

# Bunkr & Balbums alan adları
BUNKR_DOMAINS = [
    "bunkr.si", "bunkr.cr", "bunkr.is", "bunkr.to", "bunkr.ru", 
    "bunkr.sk", "bunkr.black", "bunkr.ws", "bunkr.ac", "bunkr.se",
    "balbums.st", "balbums.org"
]

# DoodStream alan adları ve aynaları (mirrors)
DOODSTREAM_DOMAINS = [
    "doodstream.com", "doodstream.co", "doodstream.net", "doodstream.org",
    "dood.to", "dood.so", "dood.cx", "dood.watch", "dood.pm", "dood.wf",
    "dood.re", "ds2play.com", "ds2video.com", "doods.pro", "dood.ws",
    "dood.li", "dood.la", "dood.sh", "dood.yt", "dood.stream", "dood.video",
    "doods.yt", "dood.fit", "myembed.top", "dood.vg", "dood.cd", "dood.work",
    "dood.cc", "dood.club", "dood.co", "dood.fun", "dood.live", "dood.online",
    "dood.party", "dood.tech", "dood.vip", "dood.website", "doods.top",
    "playmogo.com"
]

# Desteklenen Servisler
SUPPORTED_SERVICES = [
    "GoFile", "Bunkr", "Balbums", "Filester", "CyberFile", "Pixeldrain", 
    "KrakenFiles", "MEGA", "MixDrop", "DoodStream", "FileMoon"
]

# Token kayıt dosyası (kullanıcı dizini veya uygulama dizini)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "gofile_token.json")
