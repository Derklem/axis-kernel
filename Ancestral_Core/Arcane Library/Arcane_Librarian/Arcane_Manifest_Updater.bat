@echo off
cd /d "E:\Arcane Library\Arcane_Librarian"
python silent_indexer.py
python recursive_manifest_updater.py
exit
