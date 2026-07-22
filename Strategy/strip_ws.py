import sys

def strip_trailing_whitespace(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for line in lines:
            f.write(line.rstrip() + '\n')
            
if __name__ == "__main__":
    for arg in sys.argv[1:]:
        strip_trailing_whitespace(arg)
        print(f"Stripped: {arg}")
