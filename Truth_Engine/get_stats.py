import os, time

files = [
    r'D:\Infinite\Infinity\Truth_Engine\TE_Observations_Log.jsonl',
    r'D:\Infinite\Infinity\Truth_Engine\TE_Content_Nodes.jsonl',
    r'D:\Infinite\Infinity\Truth_Engine\TE_Claims_Index.jsonl',
    r'D:\Infinite\Infinity\Truth_Engine\TE_Grounding_Ledger.jsonl',
    r'D:\Infinite\Infinity\Truth_Engine\Triad_Consult.ps1',
    r'D:\Infinite\Infinity\Truth_Engine\T617_Lattice_Expander.ps1',
    r'D:\Infinite\Infinity\Truth_Engine\Strategies\T01_LogObservation.ps1',
    r'D:\Infinite\Infinity\v12_Fusion_Design.md',
    r'D:\Infinite\Infinity\v26_SovereignIntegration_Design.md',
    r'D:\Infinite\Infinity\v27_Operation_Almighty_Design.md',
    r'D:\Infinite\Infinity\Truth_Engine\Repair_Context_Packet.md',
    r'D:\Infinite\Infinity\Truth_Engine\Maya_Briefing_Immune_Logic.md',
    r'D:\Infinite\Infinity\Services\Service_Registry.json'
]

print(f"{'File':<40} | {'Created':<20} | {'Modified':<20}")
print("-" * 86)
for f in files:
    if os.path.exists(f):
        ctime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getctime(f)))
        mtime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(os.path.getmtime(f)))
        name = os.path.basename(f)
        print(f"{name:<40} | {ctime:<20} | {mtime:<20}")
    else:
        print(f"{os.path.basename(f):<40} | NOT FOUND            | NOT FOUND           ")
