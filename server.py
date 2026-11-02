#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Standalone Zero-Dependency Local Server (HTTP Server)
Tamamen Python standart kütüphanesiyle (http.server) çalışır, harici paket gerektirmez.
"""

import os
import re
import sys
import json
import time
import shutil
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.config import APP_NAME, APP_VERSION, DEFAULT_USER_AGENT
from core.utils import load_gofile_token, save_gofile_token
from core.engine import process_url, download_single_file

UI_DIR = os.path.join(BASE_DIR, "ui")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

# Global state
is_downloading = False
stop_requested = False
status_text = "Hazır"
status_color = "#22c55e"
active_items_state = {}     # {name: {current, total, speed, percent}}
completed_items_state = []
total_speed_str = "0.0 MB/s"

def get_settings():
    default_settings = {
        "download_dir": os.path.abspath(os.path.join(BASE_DIR, "downloads")),
        "threads": 3,
        "delay": 5,
        "lang": "auto",
        "gofile_token": load_gofile_token()
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_settings.update(saved)
        except Exception:
            pass
    return default_settings

def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def add_history(entry):
    hist = get_history()
    hist.insert(0, entry)
    if len(hist) > 100:
        hist = hist[:100]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def get_disk_free(folder):
    try:
        drive = os.path.splitdrive(folder)[0] or "C:"
        total, used, free = shutil.disk_usage(drive)
        return f"{free / (1024**3):.1f} GB Boşta"
    except Exception:
        return "-- GB Boşta"


class MercatcherHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Konsolu gereksiz istek loglarıyla doldurma

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ["/", "/index.html"]:
            index_file = os.path.join(UI_DIR, "index.html")
            if os.path.exists(index_file):
                with open(index_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "UI index.html not found")

        elif path in ["/mercatcher.png", "/logo.png"]:
            img_file = os.path.join(ASSETS_DIR, "mercatcher.png")
            if not os.path.exists(img_file):
                img_file = os.path.join(UI_DIR, "mercatcher.png")
            if not os.path.exists(img_file):
                img_file = os.path.join(BASE_DIR, "mercatcher.png")
            if os.path.exists(img_file):
                with open(img_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)

        elif path == "/manifest.json":
            manifest = {
                "name": "Mercatcher",
                "short_name": "Mercatcher",
                "start_url": "/",
                "display": "standalone",
                "background_color": "#070a13",
                "theme_color": "#070a13",
                "icons": [
                    {"src": "/mercatcher.png", "sizes": "1024x1024", "type": "image/png"},
                    {"src": "/mercatcher.ico", "sizes": "16x16 24x24 32x32 48x48 64x64 128x128 256x256", "type": "image/x-icon"}
                ]
            }
            content = json.dumps(manifest).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/manifest+json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        elif path in ["/favicon.ico", "/mercatcher.ico", "/mercatcher44x44.ico", "/mercatcher150x150.ico", "/mercatcher310x310.ico"]:
            fname = path.lstrip("/")
            if fname == "favicon.ico":
                fname = "mercatcher.ico" if (os.path.exists(os.path.join(ASSETS_DIR, "mercatcher.ico")) or os.path.exists(os.path.join(BASE_DIR, "mercatcher.ico"))) else "mercatcher44x44.ico"
            ico_file = os.path.join(ASSETS_DIR, fname)
            if not os.path.exists(ico_file):
                ico_file = os.path.join(UI_DIR, fname)
            if not os.path.exists(ico_file):
                ico_file = os.path.join(BASE_DIR, fname)
            if os.path.exists(ico_file):
                with open(ico_file, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/x-icon")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404)

        elif path == "/api/init":
            settings = get_settings()
            folder = settings.get("download_dir", "downloads")
            self.send_json({
                "folder_name": os.path.basename(folder) or "Downloads",
                "disk_free": get_disk_free(folder),
                "threads": settings.get("threads", 3),
                "delay": settings.get("delay", 5),
                "lang": settings.get("lang", "auto"),
                "token": settings.get("gofile_token", "")
            })

        elif path == "/api/poll":
            self.send_json({
                "is_downloading": is_downloading,
                "status_text": status_text,
                "status_color": status_color,
                "active_items": list(active_items_state.values()),
                "completed_items": completed_items_state,
                "total_speed": total_speed_str,
                "disk_free": get_disk_free(get_settings().get("download_dir", "C:\\"))
            })

        elif path == "/api/history":
            self.send_json(get_history())

        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            body = json.loads(post_data)
        except Exception:
            body = {}

        if path == "/api/start":
            self.handle_start_download(body.get("links", ""))
            self.send_json({"status": "started"})

        elif path == "/api/stop":
            global stop_requested, is_downloading, status_text, status_color
            stop_requested = True
            is_downloading = False
            status_text = "Durduruldu"
            status_color = "#ef4444"
            self.send_json({"status": "stopped"})

        elif path == "/api/choose-folder":
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            chosen = filedialog.askdirectory()
            root.destroy()
            if chosen:
                settings = get_settings()
                settings["download_dir"] = chosen
                save_settings(settings)
                self.send_json({
                    "folder_name": os.path.basename(chosen) or "Downloads",
                    "disk_free": get_disk_free(chosen)
                })
            else:
                self.send_json({})

        elif path == "/api/open-folder":
            settings = get_settings()
            folder = settings.get("download_dir", os.path.abspath("downloads"))
            os.makedirs(folder, exist_ok=True)
            if sys.platform == "win32":
                os.startfile(folder)
            self.send_json({"status": "ok"})

        elif path == "/api/set-threads":
            t = body.get("threads", 3)
            s = get_settings()
            s["threads"] = t
            save_settings(s)
            self.send_json({"status": "ok"})

        elif path == "/api/set-delay":
            d = body.get("delay", 5)
            s = get_settings()
            s["delay"] = d
            save_settings(s)
            self.send_json({"status": "ok"})

        elif path == "/api/set-lang":
            l = body.get("lang", "auto")
            s = get_settings()
            s["lang"] = l
            save_settings(s)
            self.send_json({"status": "ok"})

        elif path == "/api/set-token":
            tok = body.get("token", "")
            save_gofile_token(tok)
            s = get_settings()
            s["gofile_token"] = tok
            save_settings(s)
            self.send_json({"status": "ok"})

        elif path == "/api/clear-history":
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump([], f)
            except Exception:
                pass
            self.send_json({"status": "ok"})

        elif path == "/api/window/close":
            def close_kill():
                time.sleep(0.3)
                os._exit(0)
            threading.Thread(target=close_kill, daemon=True).start()
            self.send_json({"status": "closing"})

        else:
            self.send_error(404)

    def handle_start_download(self, links_str):
        global is_downloading, stop_requested, status_text, status_color
        global active_items_state, completed_items_state, total_speed_str

        if is_downloading:
            return

        urls = [l.strip() for l in re.split(r"[\r\n]+", links_str) if l.strip()]
        if not urls:
            return

        is_downloading = True
        stop_requested = False
        status_text = "Taranıyor..."
        status_color = "#f59e0b"
        active_items_state = {}
        completed_items_state = []
        total_speed_str = "0.0 MB/s"

        def worker():
            global is_downloading, stop_requested, status_text, status_color
            global active_items_state, completed_items_state, total_speed_str

            import requests
            settings = get_settings()
            out_dir = settings.get("download_dir", os.path.abspath("downloads"))
            delay_sec = settings.get("delay", 5)
            max_threads = settings.get("threads", 3)
            token_val = settings.get("gofile_token", "")

            session = requests.Session()
            session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

            all_items = []
            for u_idx, u in enumerate(urls):
                if stop_requested:
                    break
                found = process_url(u, session, custom_token=token_val)
                all_items.extend(found)

                if u_idx < len(urls) - 1 and delay_sec > 0 and not stop_requested:
                    time.sleep(delay_sec)

            if stop_requested or not all_items:
                is_downloading = False
                status_text = "Durduruldu" if stop_requested else "Dosya Bulunamadı"
                status_color = "#ef4444"
                return

            status_text = "İndiriliyor..."
            status_color = "#38bdf8"

            for it in all_items:
                active_items_state[it["name"]] = {
                    "name": it["name"],
                    "current": 0,
                    "total": it.get("size", 0),
                    "speed": "0.0 MB/s",
                    "percent": 0
                }

            def progress_cb(name, current, total, speed, percent):
                global total_speed_str
                spd_mb = speed / (1024 * 1024)
                total_speed_str = f"{spd_mb:.1f} MB/s"
                if name in active_items_state:
                    active_items_state[name]["current"] = current
                    active_items_state[name]["total"] = total
                    active_items_state[name]["speed"] = f"{spd_mb:.1f} MB/s"
                    active_items_state[name]["percent"] = percent

            completed = 0
            album_name = all_items[0].get("subfolder", "Media") if all_items else "Downloads"

            if delay_sec > 0:
                for it_idx, item in enumerate(all_items):
                    if stop_requested:
                        break
                    ok = download_single_file(item, out_dir, progress_func=progress_cb)
                    completed += 1
                    name = item["name"]
                    if name in active_items_state:
                        done_item = active_items_state.pop(name)
                        done_item["percent"] = 100
                        completed_items_state.append(done_item)

                    if it_idx < len(all_items) - 1 and not stop_requested:
                        time.sleep(delay_sec)
            else:
                with ThreadPoolExecutor(max_workers=max_threads) as pool:
                    futures = {pool.submit(download_single_file, it, out_dir, 1024*64, None, progress_cb): it for it in all_items}
                    for fut in futures:
                        if stop_requested:
                            break
                        it = futures[fut]
                        try:
                            ok = fut.result()
                            completed += 1
                            name = it["name"]
                            if name in active_items_state:
                                done_item = active_items_state.pop(name)
                                done_item["percent"] = 100
                                completed_items_state.append(done_item)
                        except Exception:
                            completed += 1

            add_history({
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "album": album_name,
                "count": completed,
                "size": f"{sum(it.get('size', 0) for it in all_items)/(1024*1024):.1f} MB",
                "folder": out_dir,
                "status": "Tamamlandı" if not stop_requested else "Durduruldu"
            })

            is_downloading = False
            total_speed_str = "0.0 MB/s"
            status_text = "Tamamlandı!" if not stop_requested else "Durduruldu"
            status_color = "#22c55e" if not stop_requested else "#ef4444"

        threading.Thread(target=worker, daemon=True).start()


def run_http_server(port=8765):
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, MercatcherHTTPHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run_http_server()
