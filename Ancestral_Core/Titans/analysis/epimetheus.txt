# epimetheus.py
class Epimetheus:
    def __init__(self):
        self.history = []

    def record_event(self, event, outcome):
        self.history.append({"event": event, "outcome": outcome})

    def last_event(self):
        return self.history[-1] if self.history else None
