# core/memory/librarian/librarian.py

class Librarian:
    def __init__(self):
        self.directives = []
        self.intention_map = {}

    def log_directive(self, phrase, intention):
        self.directives.append(phrase)
        self.intention_map[phrase] = intention
        print(f"[Librarian] Logged: \"{phrase}\" with intent → {intention}")

    def recall_intention(self, phrase):
        intent = self.intention_map.get(phrase, "Unknown")
        print(f"[Librarian] Recall: \"{phrase}\" was meant to → {intent}")
        return intent

    def full_log(self):
        return self.directives
