import os
import subprocess

# Ensure correct working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run the core engine
subprocess.run(["python", "core/halcyon_engine.py"])
