@echo off
title Mercatcher EXE Builder
echo ====================================================
echo           Mercatcher EXE Derleme Araci
echo ====================================================
echo.

echo [*] Gerekli kutuphaneler kontrol ediliyor...
python -m pip install -r requirements.txt

echo.
echo [*] Mercatcher.exe olusturuluyor (PyInstaller)...
python -m PyInstaller --noconsole --onefile --clean --icon="assets/mercatcher.ico" --add-data "ui;ui" --add-data "assets;assets" --collect-all cryptography --hidden-import=cryptography --hidden-import=cryptography.hazmat.bindings._rust --name "Mercatcher" mercatcher_gui.py

echo.
if exist "dist\Mercatcher.exe" (
    echo ====================================================
    echo [✓] Basarili! Mercatcher.exe olusturuldu.
    echo Konum: dist\Mercatcher.exe
    echo ====================================================
) else (
    echo [!] Hata: EXE olusturulamadi. Lutfen ciktiyi inceleyin.
)

pause
