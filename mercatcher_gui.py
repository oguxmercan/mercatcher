#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercatcher - Modern Native Desktop Launcher
"""

import os
import sys
import time
import socket
import tempfile
import threading
import subprocess
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import run_http_server

PORT = 8765

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_browser_path():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def start_server_daemon():
    try:
        run_http_server(PORT)
    except Exception as e:
        print(f"Server error: {e}")

def main():
    # 1. Sunucuyu başlat
    if not is_port_in_use(PORT):
        t = threading.Thread(target=start_server_daemon, daemon=True)
        t.start()
        for _ in range(40):
            if is_port_in_use(PORT):
                break
            time.sleep(0.1)

    url = f"http://127.0.0.1:{PORT}"

    # 2. Öncelik 1: pywebview ile gerçek native masaüstü penceresi
    # (Tarayıcı çerçevesi ve dünya ikonu olmadan, tam masaüstü uygulaması deneyimi)
    try:
        import webview
        class WindowApi:
            def __init__(self, window):
                self._w = window
            def minimize(self):
                if self._w:
                    self._w.minimize()
            def toggle_maximize(self):
                if self._w:
                    self._w.toggle_fullscreen()
            def close(self):
                if self._w:
                    self._w.destroy()

        class Holder:
            win = None

        holder = Holder()
        api = WindowApi(None)
        window = webview.create_window(
            title="Mercatcher",
            url=url,
            width=1120,
            height=740,
            min_size=(900, 600),
            frameless=True,
            easy_drag=True,
            js_api=api
        )
        api._w = window
        webview.start(debug=False)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"pywebview başlatılamadı, tarayıcı moduna geçiliyor: {e}")

    # 2. Öncelik 2: Edge App modu (Fallback)
    browser_path = find_browser_path()
    if browser_path:
        profile_dir = os.path.join(tempfile.gettempdir(), "MercatcherEdgeProfile")
        os.makedirs(profile_dir, exist_ok=True)

        cmd = [
            browser_path,
            f"--app={url}",
            "--window-size=1120,740",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        proc = subprocess.Popen(cmd)

        try:
            while True:
                if proc.poll() is not None:
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
    else:
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
