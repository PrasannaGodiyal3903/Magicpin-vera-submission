import json
from pathlib import Path

expanded_dir = Path("dataset/expanded")
tp = json.load(open(expanded_dir / "test_pairs.json"))["pairs"]
print(f"Total test pairs: {len(tp)}")

kinds = set()
for p in tp:
    tid = p["trigger_id"]
    mid = p["merchant_id"]
    cid = p["customer_id"]
    with open(expanded_dir / f"triggers/{tid}.json") as f:
        t = json.load(f)
    with open(expanded_dir / f"merchants/{mid}.json") as f:
        m = json.load(f)
    kinds.add(t["kind"])
    cust_str = f"cust={cid}" if cid else "no_cust"
    print(f"{p['test_id']}: kind={t['kind']:28} scope={t['scope']:8} cat={m['category_slug']:12} {cust_str}")

print("\nUnique trigger kinds in test pairs:", sorted(kinds))
