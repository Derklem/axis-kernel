import os

def setup():
    os.system("python -m venv venv && venv\\Scripts\\activate")
    os.system("pip install -r requirements.txt")
