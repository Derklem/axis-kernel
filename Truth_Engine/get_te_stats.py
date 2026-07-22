import os, time, glob

files = glob.glob('D:/Infinite/**/TE_*.jsonl', recursive=True)

print(f"{'File':<60} | {'Created':<20} | {'Modified':<20}")
print("-" * 106)
for f in files:
    ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getctime(f)))
    mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getmtime(f)))
    print(f"{f:<60} | {ctime:<20} | {mtime:<20}")
