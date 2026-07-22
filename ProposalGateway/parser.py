import json
import re

def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result

def reject_nan_inf(val):
    raise ValueError(f"NON_FINITE_NUMBER:{val}")

def parse_llm_output(raw_text: str) -> dict:
    """
    Safely parses an LLM string into a dictionary.
    Rejects duplicate keys, NaN, Infinity, and multiple objects.
    Rejects trailing text other than whitespace or a closing code fence.
    """
    text = raw_text.strip()
    
    # Try finding the first '{'
    start_idx = text.find('{')
    if start_idx == -1:
        raise ValueError("No JSON object found")
        
    candidate_text = text[start_idx:]
    
    decoder = json.JSONDecoder(
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nan_inf
    )
    
    try:
        data, end_idx = decoder.raw_decode(candidate_text)
        if not isinstance(data, dict):
            raise ValueError("Root element is not a JSON object")
            
        trailing = candidate_text[end_idx:].strip()
        
        # the only acceptable trailing text is a closing code fence
        if trailing and not trailing.startswith("```"):
            raise ValueError(f"TRAILING_CONTENT_DETECTED")
            
        return data
        
    except json.JSONDecodeError as e:
        raise ValueError(f"INVALID_JSON:{str(e)}")
