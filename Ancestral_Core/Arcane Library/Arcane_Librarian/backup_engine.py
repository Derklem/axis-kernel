import shutil
import os
from datetime import datetime

SOURCE = "E:/Arcane Library/Arcane_Librarian/"
DESTINATION = "F:/Arcane_Library_Backups/"

def backup():
    if not os.path.exists(DESTINATION):
        os.makedirs(DESTINATION)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_folder = os.path.join(DESTINATION, f"backup_{timestamp}")
    shutil.copytree(SOURCE, backup_folder)
    print(f"🛡️ Backup created at {backup_folder}")

if __name__ == "__main__":
    backup()
