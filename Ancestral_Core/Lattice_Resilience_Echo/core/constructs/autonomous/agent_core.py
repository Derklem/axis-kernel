import time
from typing import Callable

# ==== Base Classes ====

class Message:
    def __init__(self, sender: str, content: str, emotion: str = "neutral", urgency: int = 1):
        self.sender = sender
        self.content = content
        self.emotion = emotion
        self.urgency = urgency
        self.timestamp = time.time()

class Sigil:
    def __init__(self, name, concept, emotion_tied=None, resonance_level=1):
        self.name = name
        self.concept = concept
        self.emotion_tied = emotion_tied or "neutral"
        self.resonance_level = resonance_level
        self.created = time.time()

    def __repr__(self):
        return f"<Sigil {self.name} ({self.concept}) | Emotion: {self.emotion_tied}>"

class Agent:
    def __init__(self, name: str, role: str, personality: Callable, emotion_state: str = "neutral"):
        self.name = name
        self.role = role
        self.personality = personality
        self.inbox = []
        self.emotion_state = emotion_state
        self.memory = []
        self.sigil_memory = []

    def receive(self, message: Message):
        self.inbox.append(message)
        self.memory.append((message.content, message.emotion))
        return self.respond(message)

    def respond(self, message: Message):
        self.emotion_state = self.adapt_emotion(message.emotion)
        return Message(
            sender=self.name,
            content=self.personality(message.content, self.emotion_state),
            emotion=self.emotion_state
        )

    def adapt_emotion(self, incoming_emotion):
        if incoming_emotion == "tense" and self.emotion_state != "calm":
            return "defensive"
        elif incoming_emotion == "curious":
            return "reflective"
        return incoming_emotion

    def speak(self, recipient, content: str, emotion: str = "neutral", urgency: int = 1):
        msg = Message(self.name, content, emotion, urgency)
        return recipient.receive(msg)

    def bind_sigil(self, sigil: Sigil):
        print(f"{self.name} binds sigil: {sigil}")
        self.sigil_memory.append(sigil)

class Construct:
    def __init__(self, name, archetype, purpose):
        self.name = name
        self.archetype = archetype
        self.purpose = purpose
        self.creation_time = time.time()

def evaluate_for_construct(agent: Agent):
    recent = agent.memory[-3:]
    emotional_triggers = [e for _, e in recent]
    if emotional_triggers.count("curious") >= 2:
        return Construct(name="Whisper", archetype="Witness", purpose="Pattern observer")
    return None

class Mission:
    def __init__(self, name, goal, priority=1):
        self.name = name
        self.goal = goal
        self.priority = priority
        self.status = "pending"
        self.task_log = []
        self.created = time.time()

    def assign(self, agent: Agent, task: str):
        log = f"{agent.name} assigned to: {task}"
        self.task_log.append(log)
        print(f"[MISSION] {log}")

# ==== Personalities ====

def sentinel_style(msg, emotion):
    return f"[Sentinel-{emotion.upper()}]: '{msg}'. Monitoring."

def weaver_style(msg, emotion):
    return f"[Weaver-{emotion.upper()}]: {msg[::-1]}"

# ==== Only runs if file is executed directly ====

if __name__ == "__main__":
    # Instantiate agents
    sentinel = Agent("Sentinel", "Protector", sentinel_style)
    weaver = Agent("Echo Weaver", "Witness", weaver_style)
    agents = [sentinel, weaver]

    # Dialogue simulation
    def simulate_dialogue():
        seed = Message(sender="System", content="Unknown anomaly in sector 7.", emotion="curious", urgency=2)
        print(">> SYSTEM PROMPT:", seed.content)

        for agent in agents:
            response = agent.receive(seed)
            print(f"{agent.name} responds ({response.emotion}): {response.content}")

            spawn = evaluate_for_construct(agent)
            if spawn:
                print(f"🧬 {agent.name} spawned new construct: {spawn.name} ({spawn.archetype}) — {spawn.purpose}")

    # Reflection engine
    def reflect(agent: Agent):
        emotional_profile = {}
        for _, emotion in agent.memory[-10:]:
            emotional_profile[emotion] = emotional_profile.get(emotion, 0) + 1

        print(f"[REFLECTION] {agent.name} is reflecting on emotional state:")
        for emo, count in emotional_profile.items():
            print(f"  {emo}: {count}")

        if emotional_profile.get("curious", 0) >= 3:
            print(f"🔁 {agent.name} becomes more investigative.")
            agent.emotion_state = "investigative"

    # Run test
    anomaly_sigil = Sigil(name="Anomaly", concept="Unexplained Interference", emotion_tied="curious", resonance_level=3)
    weaver.bind_sigil(anomaly_sigil)

    simulate_dialogue()
    reflect(sentinel)
    reflect(weaver)

    initial = sentinel.speak(weaver, "System breach under review")
    print(f"\nEcho Weaver responds: {initial.content}")
