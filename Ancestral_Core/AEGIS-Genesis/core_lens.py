def interpret_intention(input_text):
    import re
    import json

    cues = {
        "fear": ["I'm worried", "I'm afraid", "what if", "concern"],
        "desire": ["I want", "I wish", "I hope", "I'd love to"],
        "deflection": ["I'm fine", "it doesn't matter", "whatever", "nevermind"],
        "control": ["should", "must", "need to", "have to"],
        "truth": ["honestly", "to be real", "truth is", "let me be straight"],
    }

    result = {}
    for intent, patterns in cues.items():
        result[intent] = any(re.search(pat, input_text, re.IGNORECASE) for pat in patterns)

    dominant = [k for k, v in result.items() if v]
    return json.dumps({"intention_profile": dominant or ["ambiguous"]}, indent=2)
