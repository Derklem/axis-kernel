
import json
import os
import re
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
INPUT_FILE = r"C:\Users\17602\Documents\Grok-Memory\grok_memory_dump_1766613811502.json"
OUTPUT_FILE = r"C:\Users\17602\Documents\Grok-Memory\SpaceX_Resolution_ARCHIVED.md"

def parse_grok_dump():
    print(f"Loading {INPUT_FILE}...")
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Error: File not found.")
        return

    html_content = data.get('html_snapshot', '')
    url = data.get('url', 'Unknown URL')
    scraped_at = data.get('scraped_at', datetime.now().isoformat())

    print("Parsing HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')

    messages = []
    
    # HEURISTIC 2.0: Button Association
    # We find all "message-bubble" divs.
    # Then we look at the 'action-buttons' container associated with it (usually sibling).
    
    # Structure typically:
    # <div id="response-..."> (Wrapper for Grok)
    #   <div class="message-bubble">...</div>
    #   <div class="action-buttons">... <button aria-label="Copy"> ...</div>
    # </div>
    
    # User messages:
    # <div class="group ...">
    #   <div class="message-bubble">...</div>
    #   <div class="action-buttons">... <button aria-label="Edit"> ...</div>
    # </div>

    # We will iterate all message-bubble divs and look for nearest distinctive buttons.

    bubbles = soup.find_all(class_='message-bubble')
    print(f"Found {len(bubbles)} message bubbles.")

    for i, bubble in enumerate(bubbles):
        text = bubble.get_text(separator='\n').strip()
        if not text:
            continue

        role = "UNKNOWN"
        
        # Look for parent container that holds both bubble and actions
        # We traverse up 2-3 levels
        container = bubble.find_parent(class_='group') or bubble.parent.parent
        
        if container:
            if container.find('button', attrs={'aria-label': 'Edit'}):
                role = "USER"
            elif container.find('button', attrs={'aria-label': 'Regenerate'}) or \
                 container.find('button', attrs={'aria-label': 'Copy'}) or \
                 container.find('button', attrs={'aria-label': 'Bad response'}) or \
                 container.get('id', '').startswith('response-'):
                role = "ASSISTANT"
            else:
                # Fallback: Alternating? Or checks specific text
                # If identifying as "Grok" or "Assistant" in text? No.
                # Assume Assistant if inside response- id
                if bubble.find_parent(id=re.compile(r'response-')):
                    role = "ASSISTANT"
                else:
                    role = "USER" # Default for non-response containers
        
        # Refinement: If previous was User, this is likely Assistant, etc?
        # No, threaded mode might break that.
        
        # Timestamp:
        # Check for <time> or any data-date attribute
        timestamp = "Unknown Time"
        # Sometimes time is in a tooltip or aria-label of the 'sent' indicator
        # We'll skip deep timestamp check for now as it seemed missing.

        messages.append({
            'role': role,
            'content': text,
            'timestamp': timestamp
        })

    # Formatting Markdown
    md_output = f"""---
title: Grok Conversation Archive
source_url: {url}
archived_at: {scraped_at}
message_count: {len(messages)}
---

# Conversation Log

"""

    for msg in messages:
        icon = "🧑‍💻" if msg['role'] == "USER" else "🤖"
        # If role is UNKNOWN, we guess based on alternating, but label it.
        if msg['role'] == "UNKNOWN":
             # Simple alternator fall back if buttons failed
             pass 

        md_output += f"### {icon} **{msg['role']}** *({msg['timestamp']})*\n\n"
        md_output += f"{msg['content']}\n\n"
        md_output += "---\n\n"

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(md_output)
    
    print(f"Successfully archived {len(messages)} messages to {OUTPUT_FILE}")

if __name__ == "__main__":
    parse_grok_dump()
