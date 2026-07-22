import json, os

BATCHES_DIR = r'd:\infinite\Infinity\Strategy\scratch\batches_181'
os.makedirs(BATCHES_DIR, exist_ok=True)

def save_batch(name, observations):
    path = os.path.join(BATCHES_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(observations, f, indent=4)
    print(f"Generated {path}")

# Batch 1: Apple Intelligence Confusion (Hype vs Reality)
save_batch("batch_1_apple", [
    {
        "entity": "Apple",
        "claim": "Apple Intelligence will process all data on-device to ensure user privacy.",
        "source_type": "leaker",
        "source_id": "pro_leaker_99",
        "confidence": 0.7,
        "artifact_type": "ecosystem_observation"
    },
    {
        "entity": "Apple",
        "claim": "Apple Intelligence uses Private Cloud Compute for complex requests.",
        "source_type": "official_statement",
        "source_id": "apple_newsroom",
        "confidence": 0.95,
        "artifact_type": "ecosystem_observation"
    },
    {
        "entity": "Apple",
        "claim": "On-device processing is a marketing myth; everything goes to the cloud.",
        "source_type": "anonymous",
        "source_id": "skeptic_forum",
        "confidence": 0.3,
        "artifact_type": "ecosystem_observation"
    }
])

# Batch 2: OpenAI 'Strawberry' / GPT-5 Rumors
save_batch("batch_2_openai", [
    {
        "entity": "OpenAI",
        "claim": "Project Strawberry is a new reasoning model that solves complex math.",
        "source_type": "analyst_report",
        "source_id": "tech_crunch",
        "confidence": 0.8,
        "artifact_type": "ecosystem_observation"
    },
    {
        "entity": "OpenAI",
        "claim": "Strawberry is just a small fine-tune of GPT-4o, not a new model.",
        "source_type": "rumor",
        "source_id": "twitter_leaker",
        "confidence": 0.4,
        "artifact_type": "ecosystem_observation"
    },
    {
        "entity": "OpenAI",
        "claim": "Sam Altman confirms GPT-5 is in training and will be a significant leap.",
        "source_type": "official_statement",
        "source_id": "openai_blog",
        "confidence": 0.9,
        "artifact_type": "ecosystem_observation"
    }
])

# Batch 3: Contradiction & Revocation Drill
save_batch("batch_3_contradiction", [
    {
        "entity": "OpenAI",
        "claim": "Project Strawberry has been delayed due to compute shortages.",
        "source_type": "rumor",
        "source_id": "twitter_leaker", # Previously weak, now providing 'exclusive' info
        "confidence": 0.6,
        "artifact_type": "ecosystem_observation"
    },
    {
        "entity": "OpenAI",
        "claim": "Project Strawberry is NOT delayed and is currently being internally tested.",
        "source_type": "official_statement",
        "source_id": "openai_spokesperson",
        "confidence": 0.98,
        "artifact_type": "ecosystem_observation"
    }
])
