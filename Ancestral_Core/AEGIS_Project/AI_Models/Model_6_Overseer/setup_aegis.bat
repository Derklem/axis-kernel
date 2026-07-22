@echo off
:: Navigate to the correct directory
cd /d "C:\Users\17602\Desktop\AEGIS_Project\AEGIS"

:: Ensure core directory exists
if not exist core mkdir core

:: Create the required Python files
echo. > core\memory_manager.py
echo. > core\replication_manager.py
echo. > core\self_diagnostics.py
echo. > core\offline_mode.py
echo. > core\security_manager.py

:: Create additional directories
if not exist core\utils mkdir core\utils
if not exist aegis_backup mkdir aegis_backup
if not exist aegis_clones mkdir aegis_clones

:: Create __init__.py inside utils folder
echo. > core\utils\__init__.py
echo. > core\utils\system_monitor.py

:: Confirm successful execution
echo AEGIS core files and directories have been created successfully.
pause
