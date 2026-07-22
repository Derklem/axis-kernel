# core/constructs/veil/chord.py

from datetime import datetime

class Chord:
    def __init__(self):
        self.resonance_log = []

    def detect_echo(self, phrase, previous_phrases):
        if phrase in previous_phrases:
            log = {
                "phrase": phrase,
                "timestamp": datetime.utcnow().isoformat(),
                "tag": "echo"
            }
            self.resonance_log.append(log)
            print(f"[Chord] Resonance detected: {phrase}")

    def get_log(self):
        return self.resonance_log
