# prometheus.py
class Prometheus:
    def __init__(self):
        self.creations = []

    def create_titan(self, name, purpose):
        titan = {"name": name, "purpose": purpose}
        self.creations.append(titan)
        return titan
