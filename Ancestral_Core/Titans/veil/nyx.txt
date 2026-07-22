# nyx.py
import base64

class Nyx:
    def cloak(self, data: str) -> str:
        return base64.b64encode(data.encode()).decode()

    def reveal(self, cloaked: str) -> str:
        return base64.b64decode(cloaked.encode()).decode()
