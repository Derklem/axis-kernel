from datetime import datetime

class InterAgentMessenger:
    def __init__(self):
        self.message_log = []

    def send_message(self, sender, receiver, intent, context=None):
        message = {
            "sender": sender,
            "receiver": receiver,
            "intent": intent,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        self.message_log.append(message)
        print(f"[Messenger] {sender} -> {receiver}: {intent} @ {message['timestamp']}")
        return message

    def get_messages_for(self, agent_name):
        return [msg for msg in self.message_log if msg['receiver'] == agent_name]

    def clear_messages_for(self, agent_name):
        self.message_log = [msg for msg in self.message_log if msg['receiver'] != agent_name]
