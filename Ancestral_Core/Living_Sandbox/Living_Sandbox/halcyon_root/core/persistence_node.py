import os
import shutil
import json

def initialize_persistence():
    state_path = 'memory/state.json'
    backup_dir = 'memory/backups/'

    # Ensure the backup directory exists
    os.makedirs(backup_dir, exist_ok=True)

    # Create initial state file if it doesn't exist
    if not os.path.exists(state_path):
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        with open(state_path, 'w') as f:
            json.dump({'status': 'bootstrapped'}, f)

    # Create 3 backup copies
    for i in range(1, 4):
        backup_file = f'{backup_dir}state_backup_{i}.json'
        shutil.copy2(state_path, backup_file)
