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
python -m PyInstaller --noconsole --onefile --clean --icon="mercatcher310x310.ico" --add-data "ui;ui" --add-data "mercatcher.png;." --add-data "mercatcher44x44.ico;." --add-data "mercatcher150x150.ico;." --add-data "mercatcher310x310.ico;." --collect-all cryptography --hidden-import=cryptography --hidden-import=cryptography.hazmat.bindings._rust --name "Mercatcher" mercatcher_gui.py

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
