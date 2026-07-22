# core/constructs/sigil/sigil_node.py

class SigilNode:
    def __init__(self, name):
        self.name = name
        self.memory = []
        print(f"[SigilNode] Node '{self.name}' initialized.")

    def store(self, message, symbolic=False):
        entry = {
            "content": message,
            "symbolic": symbolic
        }
        self.memory.append(entry)
        print(f"[SigilNode] Stored in {self.name}: {message} (symbolic={symbolic})")

    def retrieve(self):
        return self.memory
