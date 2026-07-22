# themis.py
class Themis:
    def evaluate(self, context):
        if "danger" in context:
            return "deny"
        elif "growth" in context:
            return "permit"
        return "analyze"
