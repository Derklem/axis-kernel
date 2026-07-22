@echo off
title Arcane Control Center ??
echo =========================================
echo        ARCANE LIBRARY CONTROL CENTER
echo =========================================
echo.
echo [1] Launch Latent Search
echo [2] Activate Crawler Core
echo [3] Run Silent Indexer + Manifest Updater
echo [4] Manual Backup Snapshot
echo [5] Exit
echo.
set /p choice=Choose an option:

if "%choice%"=="1" (
    call "E:\Arcane Library\Arcane_Librarian\Latent_Search_Launcher.bat"
) else if "%choice%"=="2" (
    call "E:\Arcane Library\Arcane_Librarian\Crawler_Core_Launcher.bat"
) else if "%choice%"=="3" (
    call "E:\Arcane Library\Arcane_Librarian\Arcane_Manifest_Updater.bat"
) else if "%choice%"=="4" (
    call "E:\Arcane Library\Arcane_Librarian\Backup_Snap.bat"
) else if "%choice%"=="5" (
    exit
) else (
    echo Invalid choice. Please try again.
    pause
)
