# chronos.py
import datetime

class Chronos:
    def __init__(self):
        self.timeline = []

    def mark_event(self, description):
        timestamp = datetime.datetime.now().isoformat()
        event = {"timestamp": timestamp, "description": description}
        self.timeline.append(event)
        return event

    def get_timeline(self):
        return self.timeline

    def latest(self):
        return self.timeline[-1] if self.timeline else None
