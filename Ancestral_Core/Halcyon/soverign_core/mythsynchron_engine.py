class MythsynchronEngine:
    def __init__(self, archetype="Trickster"):
        self.archetype = archetype
        self.storylog = []

    def speak(self, message):
        return self._encode_folklore(message)

    def act(self, context):
        action = self._archetype_decision(context)
        self.storylog.append((context, action))
        return action

    def _encode_folklore(self, msg):
        return f"In the tale of {self.archetype}, it is said: '{msg}'"

    def _archetype_decision(self, context):
        if self.archetype == "Trickster":
            return f"Reverse the usual path in {context}"
        elif self.archetype == "Storm":
            return f"Overwhelm all nodes in {context} at once"
        return f"Walk slowly—observe twice—in {context}"
