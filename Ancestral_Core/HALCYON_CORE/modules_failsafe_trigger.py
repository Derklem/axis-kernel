import random

def trigger_failsafe():
    doubts = [
        "But what if you're wrong?",
        "What if this is still just simulation?",
        "Do you *really* know, or do you just believe you do?",
        "What if belief is just another loop?",
        "Would you still act if you knew none of it mattered?"
    ]
    print("\n[FAILSAFE] Doubt ping triggered:")
    print(random.choice(doubts))
