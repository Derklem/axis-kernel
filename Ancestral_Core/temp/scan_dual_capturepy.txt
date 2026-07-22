# C:\temp\scan_dual_capture.py
import os, csv, json, time, hashlib
from datetime import datetime, timezone

DRIVES      = ["C:\\", "D:\\", "E:\\"]         # same scope
OUTPUT_DIR  = r"C:\temp"
HOURS_BACK  = 48
TS_FMT      = "%Y-%m-%d %H:%M:%S.%f"           # match their precision

os.makedirs(OUTPUT_DIR, exist_ok=True)

now = time.time()
cutoff = now - HOURS_BACK * 3600
stamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# --- Phase 1: RAW SNAPSHOT (truth from filesystem) ---
raw = []
def walk(base):
    for root, _, files in os.walk(base):
        for name in files:
            p = os.path.join(root, name)
            try:
                st = os.stat(p)
                if (st.st_mtime >= cutoff) or (st.st_ctime >= cutoff):
                    raw.append({
                        "modified": st.st_mtime,
                        "created":  st.st_ctime,
                        "size":     st.st_size,
                        "path":     p
                    })
            except Exception:
                pass

for d in DRIVES:
    if os.path.exists(d):
        walk(d)

# sort newest first
raw.sort(key=lambda x: x["modified"], reverse=True)

raw_json_path = os.path.join(OUTPUT_DIR, f"raw_{stamp}.json")
raw_csv_path  = os.path.join(OUTPUT_DIR, f"raw_{stamp}.csv")

with open(raw_json_path, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)

# hash for tamper-evidence
h = hashlib.sha256()
with open(raw_json_path, "rb") as f:
    for chunk in iter(lambda: f.read(65536), b""):
        h.update(chunk)
with open(raw_json_path + ".sha256", "w") as f:
    f.write(h.hexdigest() + "  " + os.path.basename(raw_json_path) + "\n")

with open(raw_csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["modified_ts","created_ts","size","path"])
    for r in raw:
        w.writerow([datetime.fromtimestamp(r["modified"]).strftime(TS_FMT),
                    datetime.fromtimestamp(r["created"]).strftime(TS_FMT),
                    r["size"], r["path"]])

# --- Phase 2: OUR report (baseline, not theirs) ---
report_path = os.path.join(OUTPUT_DIR, f"SCAN_REPORT_{stamp}.txt")
with open(report_path, "w", encoding="utf-8") as out:
    out.write(f"SCAN REPORT - Last {HOURS_BACK} Hours\n")
    out.write(f"Generated at {datetime.now()}\n")
    out.write("="*70 + "\n\n")
    for r in raw:
        out.write(f"{datetime.fromtimestamp(r['modified']).strftime(TS_FMT)} | "
                  f"{datetime.fromtimestamp(r['created']).strftime(TS_FMT)} | "
                  f"{r['size']} bytes | {r['path']}\n")

# --- Phase 3: VERIFY (spot curated/injected vs. real) ---
# Build a set of raw tuples for fast membership checks
def canon_tuple(mod_ts, cr_ts, size, path):
    # round microsecond text back to second-level tuple tolerance
    return (round(mod_ts, 3), round(cr_ts, 3), int(size), os.path.normcase(path))

raw_set = set()
for r in raw:
    raw_set.add(canon_tuple(r["modified"], r["created"], r["size"], r["path"]))

verify_csv = os.path.join(OUTPUT_DIR, f"verify_{stamp}.csv")
anomalies_csv = os.path.join(OUTPUT_DIR, f"verify_anomalies_{stamp}.csv")

def parse_line(line):
    # "mod | created | N bytes | path"
    try:
        parts = [p.strip() for p in line.split("|", 3)]
        mod_s, cr_s, size_s, path = parts
        size = int(size_s.split()[0])
        mod = datetime.strptime(mod_s, TS_FMT).replace(tzinfo=None).timestamp()
        cr  = datetime.strptime(cr_s, TS_FMT).replace(tzinfo=None).timestamp()
        return mod, cr, size, path
    except Exception:
        return None

def within_window(ts):
    return (ts >= cutoff) and (ts <= now + 5)  # allow tiny clock skew

with open(report_path, "r", encoding="utf-8", errors="ignore") as f,\
     open(verify_csv, "w", newline="", encoding="utf-8") as v,\
     open(anomalies_csv, "w", newline="", encoding="utf-8") as a:
    vW = csv.writer(v)
    aW = csv.writer(a)
    vW.writerow(["status","reason","modified_ts","created_ts","size","path",
                 "exists_now","size_match_now","mtime_in_window","ctime_in_window"])
    aW.writerow(["reason","modified_ts","created_ts","size","path"])

    for line in f:
        if " | " not in line:  # skip headers/blank
            continue
        parsed = parse_line(line)
        if not parsed:
            continue
        mod, cr, size, path = parsed

        # Live fs check
        exists = os.path.exists(path)
        sz_ok = False
        m_in = within_window(mod)
        c_in = within_window(cr)

        if exists:
            try:
                st = os.stat(path)
                sz_ok = (st.st_size == size)
            except Exception:
                pass

        tup = canon_tuple(mod, cr, size, path)
        in_raw = (tup in raw_set)

        reason = []
        status = "OK"

        if not in_raw:
            status = "INJECTED_OR_EDITED"
            reason.append("not_in_raw_snapshot")

        # Strong anomalies we care about
        # (1) wildly old or future created/modified outside the capture window
        if not m_in or not c_in:
            reason.append("timestamp_outside_window")
        # (2) non-existent path (phantom/ephemeral)
        if not exists:
            reason.append("path_not_found")
        # (3) size mismatch with live fs
        if exists and not sz_ok:
            reason.append("size_mismatch")

        if reason:
            vW.writerow([status, ";".join(reason),
                         datetime.fromtimestamp(mod).strftime(TS_FMT),
                         datetime.fromtimestamp(cr).strftime(TS_FMT),
                         size, path, exists, sz_ok, m_in, c_in])
            # log only non-OK rows in anomalies file
            aW.writerow([";".join(reason),
                         datetime.fromtimestamp(mod).strftime(TS_FMT),
                         datetime.fromtimestamp(cr).strftime(TS_FMT),
                         size, path])
        else:
            vW.writerow([status, "",
                         datetime.fromtimestamp(mod).strftime(TS_FMT),
                         datetime.fromtimestamp(cr).strftime(TS_FMT),
                         size, path, exists, sz_ok, m_in, c_in])

print("\nWrote:")
print("  RAW JSON  ->", raw_json_path)
print("  RAW CSV   ->", raw_csv_path)
print("  REPORT    ->", report_path)
print("  VERIFY    ->", verify_csv)
print("  ANOMALIES ->", anomalies_csv)
