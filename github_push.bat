@echo off
cd /d "%~dp0"
title GitHub Push - Mercatcher
echo ====================================================
echo           Mercatcher GitHub'a Yukleniyor...
echo ====================================================
echo.
echo [*] Kodlar GitHub'a gonderiliyor...
echo [*] Eger oturum acilmamissa karsiniza tarayici onay penceresi gelecektir.
echo.
git push -u origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ====================================================
    echo [✓] Tebrikler! Kodlar GitHub'a basariyla yuklendi!
    echo ====================================================
) else (
    echo [!] Yukleme sirasinda bir sorun olustu.
)
echo.
pause
