#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Command Line Interface (CLI)
"""

import os
import re
import sys
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.config import APP_NAME, APP_VERSION, DEFAULT_USER_AGENT
from core.engine import process_url, download_single_file

def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - Gofile.io ve Bunkr.si Toplu Video/Fotoğraf İndirici"
    )
    parser.add_argument("links", nargs="*", help="İndirilecek bağlantılar veya link içeren .txt dosyası")
    parser.add_argument("-o", "--output", default="downloads", help="Hedef indirme klasörü (varsayılan: downloads)")
    parser.add_argument("-t", "--threads", type=int, default=4, help="Eşzamanlı indirme sayısı (varsayılan: 4)")
    parser.add_argument("--token", type=str, default="", help="Gofile hesap tokeni (isteğe bağlı)")

    args = parser.parse_args()

    input_links = []
    if args.links:
        for item in args.links:
            if os.path.isfile(item):
                with open(item, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            input_links.append(line)
            else:
                input_links.append(item)
    else:
        print("=" * 60)
        print(f"   {APP_NAME} v{APP_VERSION} - Bulk Media Downloader")
        print("=" * 60)
        user_input = input("İndirmek istediğiniz linki yapıştırın: ").strip()
        if not user_input:
            print("Link girilmedi. Çıkılıyor.")
            sys.exit(0)
        input_links = [l.strip() for l in re.split(r"[\s,]+", user_input) if l.strip()]

    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    all_download_items = []
    for link in input_links:
        items = process_url(link, session, custom_token=args.token)
        all_download_items.extend(items)

    total_files = len(all_download_items)
    print(f"\n{'=' * 60}")
    print(f"Toplam İndirilecek Öğe Sayısı: {total_files}")
    print(f"Hedef Klasör: {os.path.abspath(args.output)}")
    print(f"Eşzamanlı İndirme (Threads): {args.threads}")
    print(f"{'=' * 60}\n")

    if total_files == 0:
        print("[!] İndirilecek dosya bulunamadı veya link çözümlenemedi.")
        return

    success_count = 0
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(download_single_file, item, args.output): item
            for item in all_download_items
        }
        for fut in as_completed(futures):
            if fut.result():
                success_count += 1

    print(f"\n[✓] Tamamlandı! Başarılı: {success_count}/{total_files}")


if __name__ == "__main__":
    main()
