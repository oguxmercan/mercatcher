#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - MEGA Çıkarıcı (Extractor)
mega.nz ve mega.io üzerindeki dosyaları ve klasörleri çözer.
Standart cryptography kütüphanesini kullanarak istemci tarafında akış halinde (streaming) çözer.
"""

import os
import re
import json
import base64
import struct
import random
import requests

from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename

def get_aes_cbc_decryptor(key: bytes, iv: bytes):
    """AES-CBC decryptor nesnesi döndürür (cryptography veya pycryptodome)."""
    # 1. cryptography dene
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        return cipher.decryptor()
    except Exception:
        pass

    # 2. pycryptodome dene
    try:
        from Crypto.Cipher import AES
        return AES.new(key, AES.MODE_CBC, iv=iv)
    except Exception:
        pass

    return None

def get_aes_ecb_decryptor(key: bytes):
    """AES-ECB decryptor nesnesi döndürür."""
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.backends import default_backend
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        return cipher.decryptor()
    except Exception:
        pass

    try:
        from Crypto.Cipher import AES
        return AES.new(key, AES.MODE_ECB)
    except Exception:
        pass

    return None

def b64_decode(data: str) -> bytes:
    """MEGA URL-safe Base64 çözücü."""
    data = data.replace("-", "+").replace("_", "/")
    data += "=" * (-len(data) % 4)
    return base64.b64decode(data)

def decrypt_attr(attr_b64: str, key: bytes) -> dict:
    """Dosya adı vb. meta verileri çözer."""
    try:
        decryptor = get_aes_cbc_decryptor(key, b"\x00" * 16)
        if not decryptor:
            return {}
        raw_cipher = b64_decode(attr_b64)
        if hasattr(decryptor, "update"):
            raw = decryptor.update(raw_cipher) + (decryptor.finalize() if hasattr(decryptor, "finalize") else b"")
        elif hasattr(decryptor, "decrypt"):
            raw = decryptor.decrypt(raw_cipher)
        else:
            return {}

        if raw.startswith(b"MEGA{"):
            closing = raw.rfind(b"}")
            if closing != -1:
                return json.loads(raw[4:closing + 1].decode("utf-8", errors="ignore"))
    except Exception:
        pass
    return {}

class MegaExtractor:
    def __init__(self, session: requests.Session, log_func=None):
        self.session = session
        self.log = log_func or print

    def is_mega_url(self, url: str) -> bool:
        return "mega.nz" in url or "mega.io" in url or "mega.co.nz" in url

    def extract(self, url: str) -> list:
        url = url.strip()
        # 1. Klasör mü? (/folder/ID#KEY veya /#F!ID!KEY)
        folder_match = re.search(r"mega\.(?:nz|io|co\.nz)/(?:folder/|#F!)([a-zA-Z0-9_-]+)[#!]([a-zA-Z0-9_-]+)", url)
        if folder_match:
            folder_id, folder_key = folder_match.groups()
            return self.extract_folder(folder_id, folder_key)

        # 2. Tekil Dosya mı? (/file/ID#KEY veya /#!ID!KEY)
        file_match = re.search(r"mega\.(?:nz|io|co\.nz)/(?:file/|#!)([a-zA-Z0-9_-]+)[#!]([a-zA-Z0-9_-]+)", url)
        if file_match:
            file_id, file_key = file_match.groups()
            item = self.extract_single_file(file_id, file_key)
            return [item] if item else []

        self.log(f"[!] Tanınmayan MEGA bağlantı formatı: {url}")
        return []

    def extract_single_file(self, file_id: str, file_key_b64: str) -> dict:
        self.log(f"[*] MEGA dosyası çözümleniyor: {file_id}")
        try:
            raw_key = b64_decode(file_key_b64)
            if len(raw_key) != 32:
                self.log("[!] Geçersiz MEGA anahtar boyutu.")
                return None

            k = struct.unpack(">8I", raw_key)
            aes_key = struct.pack(">4I", k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
            iv = struct.pack(">4I", k[4], k[5], 0, 0)

            # MEGA API isteği
            req_id = random.randint(1000000000, 9999999999)
            api_url = f"https://g.api.mega.co.nz/cs?id={req_id}"
            payload = [{"a": "g", "g": 1, "p": file_id}]

            resp = self.session.post(api_url, json=payload, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=25)
            if resp.status_code != 200:
                self.log(f"[!] MEGA API yanıt vermedi (HTTP {resp.status_code})")
                return None

            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                res_obj = data[0]
                if isinstance(res_obj, int):
                    self.log(f"[!] MEGA Hata Kodu: {res_obj} (Dosya silinmiş veya erişim engellenmiş)")
                    return None

                download_url = res_obj.get("g")
                size = res_obj.get("s", 0)
                at = res_obj.get("at", "")

                attr_data = decrypt_attr(at, aes_key)
                filename = sanitize_filename(attr_data.get("n") or f"mega_{file_id}")

                self.log(f"[✓] MEGA Dosyası Hazır: {filename} ({size} bayt)")
                return {
                    "name": filename,
                    "url": download_url,
                    "size": size,
                    "subfolder": "MEGA",
                    "headers": {"User-Agent": DEFAULT_USER_AGENT},
                    "is_mega": True,
                    "mega_key": aes_key.hex(),
                    "mega_iv": iv.hex()
                }

        except Exception as e:
            self.log(f"[!] MEGA dosya ayrıştırma hatası: {e}")

        return None

    def extract_folder(self, folder_id: str, folder_key_b64: str) -> list:
        self.log(f"[*] MEGA klasörü taranıyor: {folder_id}")
        try:
            raw_key = b64_decode(folder_key_b64)
            if len(raw_key) != 16:
                self.log("[!] Geçersiz MEGA klasör anahtarı.")
                return []

            req_id = random.randint(1000000000, 9999999999)
            api_url = f"https://g.api.mega.co.nz/cs?id={req_id}&n={folder_id}"
            payload = [{"a": "f", "c": 1, "r": 1}]

            resp = self.session.post(api_url, json=payload, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=30)
            if resp.status_code != 200:
                self.log(f"[!] MEGA Klasör API yanıt vermedi (HTTP {resp.status_code})")
                return []

            data = resp.json()
            if not isinstance(data, list) or not data or not isinstance(data[0], dict):
                return []

            nodes = data[0].get("f", [])
            self.log(f"[+] MEGA klasöründe {len(nodes)} nesne bulundu.")

            # Klasör adını ve dosyaları ayıkla
            items = []
            for n in nodes:
                t = n.get("t", 0)  # 0: dosya, 1: klasör
                if t == 0:  # Dosya
                    h = n.get("h")
                    k_str = n.get("k", "")
                    s = n.get("s", 0)
                    a = n.get("a", "")

                    # Dosya anahtarını çöz
                    # Klasör altındaki dosyaların anahtarı klasör anahtarıyla şifrelidir
                    key_part = k_str.split("/")[-1].split(":")[-1] if ":" in k_str else k_str
                    try:
                        dec_key_cipher = get_aes_ecb_decryptor(raw_key)
                        if not dec_key_cipher:
                            continue
                        cipher_data = b64_decode(key_part)
                        if hasattr(dec_key_cipher, "update"):
                            raw_file_key = dec_key_cipher.update(cipher_data) + (dec_key_cipher.finalize() if hasattr(dec_key_cipher, "finalize") else b"")
                        elif hasattr(dec_key_cipher, "decrypt"):
                            raw_file_key = dec_key_cipher.decrypt(cipher_data)
                        else:
                            continue

                        if len(raw_file_key) >= 32:
                            k = struct.unpack(">8I", raw_file_key[:32])
                            aes_key = struct.pack(">4I", k[0] ^ k[4], k[1] ^ k[5], k[2] ^ k[6], k[3] ^ k[7])
                            iv = struct.pack(">4I", k[4], k[5], 0, 0)

                            attr_data = decrypt_attr(a, aes_key)
                            fname = sanitize_filename(attr_data.get("n") or f"file_{h}")

                            # Dosya indirme linkini al
                            dl_payload = [{"a": "g", "g": 1, "n": h}]
                            dl_resp = self.session.post(f"https://g.api.mega.co.nz/cs?id={random.randint(1000,9999)}&n={folder_id}", json=dl_payload, timeout=20)
                            if dl_resp.status_code == 200:
                                dl_data = dl_resp.json()
                                if isinstance(dl_data, list) and len(dl_data) > 0 and isinstance(dl_data[0], dict):
                                    g_url = dl_data[0].get("g")
                                    if g_url:
                                        items.append({
                                            "name": fname,
                                            "url": g_url,
                                            "size": s,
                                            "subfolder": f"MEGA_{folder_id}",
                                            "headers": {"User-Agent": DEFAULT_USER_AGENT},
                                            "is_mega": True,
                                            "mega_key": aes_key.hex(),
                                            "mega_iv": iv.hex()
                                        })
                    except Exception:
                        continue

            self.log(f"[✓] MEGA klasöründen {len(items)} dosya hazırlandı.")
            return items

        except Exception as e:
            self.log(f"[!] MEGA klasör çıkarma hatası: {e}")
            return []
