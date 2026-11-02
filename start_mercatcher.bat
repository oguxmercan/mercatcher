@echo off
cd /d "%~dp0"
title Mercatcher
python mercatcher_gui.py
if errorlevel 1 pause
