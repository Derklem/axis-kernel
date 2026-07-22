
import json
import os
import re
import glob
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
INPUT_DIR = r"C:\Users\17602\Documents\Grok-Memory"
OUTPUT_FILE = r"C:\Users\17602\Documents\Grok-Memory\GROK_MEMORY_FULL.md"

def parse_html_content(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    messages = []
    
    bubbles = soup.find_all(class_='message-bubble')

    for i, bubble in enumerate(bubbles):
        text = bubble.get_text(separator='\n').strip()
        if not text:
            continue
        
        # Filter noise
        if text in ["Toggle Sidebar", "Share", "New Chat"]:
            continue

        role = "UNKNOWN"
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
                if bubble.find_parent(id=re.compile(r'response-')):
                    role = "ASSISTANT"
                else:
                    role = "USER"
        
        messages.append({
            'role': role,
            'content': text
        })
    return messages

def integrate_dumps():
    print(f"Scanning {INPUT_DIR}...")
    files = glob.glob(os.path.join(INPUT_DIR, "grok_memory_dump_*.json"))
    print(f"Found {len(files)} dumps.")

    # Group by URL to dedup
    conversations = {} # url -> {timestamp, file, size, data}

    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                url = data.get('url', 'UNKNOWN_URL')
                # Normalizing URL (remove query params if needed? No, rid might be conversation ID)
                # Let's keep full URL.
                
                # Heuristic: Keep the LARGEST file for a given URL (most history loaded)
                if url not in conversations:
                    conversations[url] = {'file': fpath, 'data': data, 'size': os.path.getsize(fpath)}
                else:
                    if os.path.getsize(fpath) > conversations[url]['size']:
                        conversations[url] = {'file': fpath, 'data': data, 'size': os.path.getsize(fpath)}
        except Exception as e:
            print(f"Failed to load {fpath}: {e}")

    print(f"Consolidated into {len(conversations)} unique conversations.")

    # Process and Sort
    processed_convos = []
    
    for url, item in conversations.items():
        data = item['data']
        print(f"Processing {url[:50]}... from {os.path.basename(item['file'])}")
        
        msgs = parse_html_content(data.get('html_snapshot', ''))
        
        # Extract title from first message or raw text
        title = "Untitled Conversation"
        if msgs:
            title = msgs[0]['content'][:50].replace('\n', ' ') + "..."
        
        processed_convos.append({
            'url': url,
            'scraped_at': data.get('scraped_at'),
            'messages': msgs,
            'title': title
        })

    # Generate Markdown
    # Sort by scraped_at
    processed_convos.sort(key=lambda x: x['scraped_at'] or "")

    md_output = f"""# GROK MEMORY AGGREGATION
**Generated:** {datetime.now().isoformat()}
**Total Conversations:** {len(processed_convos)}
**Total Messages:** {sum(len(c['messages']) for c in processed_convos)}

---

## Index
"""
    for i, conv in enumerate(processed_convos):
        md_output += f"{i+1}. [{conv['title']}](#conversation-{i+1})\n"

    md_output += "\n---\n"

    for i, conv in enumerate(processed_convos):
        md_output += f"\n## Conversation {i+1}\n"
        md_output += f"**Source:** {conv['url']}\n"
        md_output += f"**Scraped:** {conv['scraped_at']}\n\n"
        
        for msg in conv['messages']:
            icon = "🧑‍💻" if msg['role'] == "USER" else "🤖"
            content = msg['content'].replace('\n', '\n> ') # Blockquote style
            md_output += f"### {icon} {msg['role']}\n"
            md_output += f"{msg['content']}\n\n"
            md_output += "---\n"

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(md_output)

    print(f"Full memory integrated to {OUTPUT_FILE}")
    
    # Resonance Output
    msg_count = sum(len(c['messages']) for c in processed_convos)
    if msg_count > 100:
        print("RESONANCE_METAMORPHOSIS_DETECTED")

if __name__ == "__main__":
    integrate_dumps()
