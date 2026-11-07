#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - İndirme Motoru
"""

import os
import time
import urllib.parse
import requests

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

from .config import DEFAULT_USER_AGENT
from .utils import sanitize_filename
from .gofile import GofileExtractor
from .bunkr import BunkrExtractor
from .pixeldrain import PixeldrainExtractor
from .krakenfiles import KrakenFilesExtractor
from .cyberfile import CyberFileExtractor
from .filester import FilesterExtractor
from .mixdrop import MixDropExtractor
from .doodstream import DoodStreamExtractor
from .filemoon import FileMoonExtractor
from .ifsaturk import IfsaTurkExtractor
from .mega import MegaExtractor

def download_single_file(item: dict, base_dir: str, chunk_size: int = 1024 * 64, log_func=None, progress_func=None) -> bool:
    """Tek bir dosyayı progress bar, hız takibi ve resume kontrolü ile indirir."""
    logger = log_func or print
    name = item["name"]
    url = item["url"]
    subfolder = item.get("subfolder", "")
    headers = item.get("headers", {})
    is_mega = item.get("is_mega", False)

    target_dir = os.path.join(base_dir, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, name)

    expected_size = item.get("size", 0)
    if os.path.exists(target_path):
        current_size = os.path.getsize(target_path)
        if expected_size and current_size == expected_size:
            logger(f"[✓ Zaten Var] {name}")
            if progress_func:
                progress_func(name, expected_size, expected_size, 0, 100)
            return True
        elif not expected_size and current_size > 0:
            logger(f"[✓ Zaten Var] {name}")
            if progress_func:
                progress_func(name, current_size, current_size, 0, 100)
            return True

    temp_path = target_path + ".part"
    mode = "wb"
    resume_header = {}
    current_bytes = 0

    if os.path.exists(temp_path) and not is_mega:
        current_bytes = os.path.getsize(temp_path)
        resume_header["Range"] = f"bytes={current_bytes}-"
        mode = "ab"

    combined_headers = {**headers, **resume_header}

    # Mega ise şifre çözücüyü hazırla
    mega_decryptor = None
    if is_mega and "mega_key" in item and "mega_iv" in item:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            from cryptography.hazmat.backends import default_backend
            k_bytes = bytes.fromhex(item["mega_key"])
            iv_bytes = bytes.fromhex(item["mega_iv"])
            cipher = Cipher(algorithms.AES(k_bytes), modes.CTR(iv_bytes), backend=default_backend())
            mega_decryptor = cipher.decryptor()
        except Exception:
            try:
                from Crypto.Cipher import AES
                from Crypto.Util import Counter
                k_bytes = bytes.fromhex(item["mega_key"])
                iv_bytes = bytes.fromhex(item["mega_iv"])
                ctr = Counter.new(128, initial_value=int.from_bytes(iv_bytes, byteorder='big'))
                mega_decryptor = AES.new(k_bytes, AES.MODE_CTR, counter=ctr)
            except Exception as ce:
                logger(f"[!] Mega decryptor başlatılamadı: {ce}")

    try:
        with requests.get(url, headers=combined_headers, stream=True, timeout=30) as r:
            if r.status_code in [416, 403, 401] and current_bytes > 0:
                mode = "wb"
                current_bytes = 0
                combined_headers.pop("Range", None)
                r = requests.get(url, headers=combined_headers, stream=True, timeout=30)

            r.raise_for_status()

            total_size = int(r.headers.get("content-length", 0))
            if mode == "ab":
                total_size += current_bytes
            if not total_size and expected_size:
                total_size = expected_size

            progress_bar = None
            if tqdm and not log_func:
                progress_bar = tqdm(
                    total=total_size if total_size > 0 else None,
                    initial=current_bytes,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                    desc=name[:25].ljust(25),
                    leave=False
                )

            last_speed_time = time.time()
            last_speed_bytes = current_bytes
            current_speed = 0.0

            with open(temp_path, mode) as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        if mega_decryptor:
                            if hasattr(mega_decryptor, "update"):
                                chunk = mega_decryptor.update(chunk)
                            elif hasattr(mega_decryptor, "decrypt"):
                                chunk = mega_decryptor.decrypt(chunk)

                        f.write(chunk)
                        current_bytes += len(chunk)
                        if progress_bar is not None:
                            progress_bar.update(len(chunk))

                        now = time.time()
                        time_diff = now - last_speed_time
                        if time_diff >= 0.4:
                            current_speed = (current_bytes - last_speed_bytes) / time_diff
                            last_speed_time = now
                            last_speed_bytes = current_bytes
                            if progress_func:
                                percent = int((current_bytes / total_size) * 100) if total_size > 0 else 0
                                progress_func(name, current_bytes, total_size, current_speed, percent)

            if progress_bar is not None:
                progress_bar.close()

        if os.path.exists(target_path):
            os.remove(target_path)
        os.rename(temp_path, target_path)

        if progress_func:
            final_size = total_size if total_size > 0 else current_bytes
            progress_func(name, final_size, final_size, 0, 100)

        logger(f"[✓ Tamamlandı] {name}")
        return True

    except Exception as e:
        logger(f"[✗ Hata] {name}: {e}")
        return False


def process_url(url: str, session: requests.Session, log_func=None, custom_token: str = None) -> list:
    """Verilen URL türünü tespit eder ve indirilecek öğe listesini döndürür."""
    logger = log_func or print
    url = url.strip()
    if not url:
        return []

    logger(f"\n[+] URL Analiz Ediliyor: {url}")

    # 1. GOFILE
    if "gofile.io" in url:
        gf = GofileExtractor(session, token=custom_token, log_func=logger)
        content_id = gf.parse_content_id(url)
        if content_id:
            logger(f"[*] Gofile ID: {content_id}")
            return gf.fetch_folder_items(content_id)
        else:
            logger("[!] Geçersiz Gofile URL'si!")
            return []

    # 2. BUNKR & BALBUMS
    bunkr = BunkrExtractor(session, log_func=logger)
    if bunkr.is_bunkr_url(url):
        tag = "Balbums" if "balbums" in url.lower() else "Bunkr"
        if "/a/" in url or "/album/" in url:
            logger(f"[*] {tag} albümü algılandı.")
            return bunkr.extract_album(url)
        elif any(f"/{x}/" in url for x in ["v", "i", "d"]):
            logger(f"[*] {tag} tekil medya algılandı.")
            item = bunkr.extract_single_media(url)
            return [item] if item else []
        else:
            return bunkr.extract_album(url)

    # 3. PIXELDRAIN
    pixeldrain = PixeldrainExtractor(session, log_func=logger)
    if pixeldrain.is_pixeldrain_url(url):
        logger("[*] Pixeldrain bağlantısı algılandı.")
        return pixeldrain.extract(url)

    # 4. KRAKENFILES
    kraken = KrakenFilesExtractor(session, log_func=logger)
    if kraken.is_kraken_url(url):
        logger("[*] KrakenFiles bağlantısı algılandı.")
        return kraken.extract(url)

    # 5. CYBERFILE
    cyberfile = CyberFileExtractor(session, log_func=logger)
    if cyberfile.is_cyberfile_url(url):
        logger("[*] CyberFile bağlantısı algılandı.")
        return cyberfile.extract(url)

    # 6. FILESTER
    filester = FilesterExtractor(session, log_func=logger)
    if filester.is_filester_url(url):
        logger("[*] Filester bağlantısı algılandı.")
        return filester.extract(url)

    # 7. MEGA
    mega = MegaExtractor(session, log_func=logger)
    if mega.is_mega_url(url):
        logger("[*] MEGA bağlantısı algılandı.")
        return mega.extract(url)

    # 8. MIXDROP
    mixdrop = MixDropExtractor(session, log_func=logger)
    if mixdrop.is_mixdrop_url(url):
        logger("[*] MixDrop bağlantısı algılandı.")
        return mixdrop.extract(url)

    # 9. DOODSTREAM
    dood = DoodStreamExtractor(session, log_func=logger)
    if dood.is_dood_url(url):
        logger("[*] DoodStream bağlantısı algılandı.")
        return dood.extract(url)

    # 10. FILEMOON
    filemoon = FileMoonExtractor(session, log_func=logger)
    if filemoon.is_filemoon_url(url):
        logger("[*] FileMoon bağlantısı algılandı.")
        return filemoon.extract(url)

    # 11. IFSATURK
    ifsaturk = IfsaTurkExtractor(session, log_func=logger)
    if ifsaturk.is_ifsaturk_url(url):
        logger("[*] İfsaTürk bağlantısı algılandı.")
        return ifsaturk.extract(url)

    # 12. GENEL DİREKT LİNK
    parsed = urllib.parse.urlparse(url)
    filename = os.path.basename(parsed.path) or f"download_{int(time.time())}"
    filename = sanitize_filename(filename)
    return [{
        "name": filename,
        "url": url,
        "size": 0,
        "subfolder": "Direct_Downloads",
        "headers": {"User-Agent": DEFAULT_USER_AGENT}
    }]
