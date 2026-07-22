import time  # Add this import at the top of the file

def construct_message(sender, recipient, content):
    # Construct a message dictionary
    message = {
        "sender": sender.name,
        "recipient": recipient.name,
        "content": content,
        "timestamp": time.time(),  # This now works because time is imported
    }
    return message

def deliver_message(message, recipients):
    for recipient_name, recipient in recipients.items():
        print(f"Message from {message['sender']} to {recipient_name}: {message['content']}")
        recipient.receive_input(message['content'])  # Pass message content to recipient's receive_input
# core/constructs/autonomous/inter_agent_language.py

def construct_message(sender, target, content, urgency=1):
    return {
        "from": sender.name,
        "to": target.name,
        "content": content,
        "urgency": urgency,
        "timestamp": time.time()
    }

def deliver_message(message, agents_registry):
    to_agent = agents_registry.get(message["to"])
    if to_agent:
        to_agent.receive_input(message["content"], source=message["from"])
        print(f"[Message] {message['from']} → {message['to']}: {message['content']}")
    else:
        print(f"[Message] Delivery failed. No agent found with name: {message['to']}")
