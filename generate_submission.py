#!/usr/bin/env python3
"""
Generates the official submission.jsonl containing the 30 canonical test pair messages.
"""

import json
import sys
from pathlib import Path
from bot import compose

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def main():
    base_dir = Path(__file__).resolve().parent
    expanded_dir = base_dir / "dataset" / "expanded"
    test_pairs_path = expanded_dir / "test_pairs.json"
    
    if not test_pairs_path.exists():
        print(f"Error: {test_pairs_path} does not exist. Run dataset generator first.")
        return

    with open(test_pairs_path, encoding="utf-8") as f:
        pairs = json.load(f)["pairs"]

    print(f"Generating submission.jsonl for {len(pairs)} canonical test pairs...")
    
    submission_path = base_dir / "submission.jsonl"
    lines = []
    
    for pair in pairs:
        test_id = pair["test_id"]
        trigger_id = pair["trigger_id"]
        merchant_id = pair["merchant_id"]
        customer_id = pair.get("customer_id")
        
        with open(expanded_dir / "triggers" / f"{trigger_id}.json", encoding="utf-8") as f:
            trigger = json.load(f)
            
        with open(expanded_dir / "merchants" / f"{merchant_id}.json", encoding="utf-8") as f:
            merchant = json.load(f)
            
        cat_slug = merchant.get("category_slug", "dentists")
        with open(expanded_dir / "categories" / f"{cat_slug}.json", encoding="utf-8") as f:
            category = json.load(f)
            
        customer = None
        if customer_id:
            cust_file = expanded_dir / "customers" / f"{customer_id}.json"
            if cust_file.exists():
                with open(cust_file, encoding="utf-8") as f:
                    customer = json.load(f)

        result = compose(category, merchant, trigger, customer)
        
        submission_entry = {
            "test_id": test_id,
            "body": result["body"],
            "cta": result["cta"],
            "send_as": result["send_as"],
            "suppression_key": result["suppression_key"],
            "rationale": result["rationale"]
        }
        lines.append(json.dumps(submission_entry, ensure_ascii=False))
        print(f"[{test_id}] {trigger['kind'][:22]:22} -> ({result['send_as']:18}) {result['body'][:60]}...")

    with open(submission_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"\nSuccessfully generated {len(lines)} lines in {submission_path}")

if __name__ == "__main__":
    main()
