import json
import re
from pathlib import Path
from bot import compose

BASE_DIR = Path(__file__).resolve().parent.parent
EXPANDED_DIR = BASE_DIR / "dataset" / "expanded"

URL_REGEX = re.compile(r'https?://[^\s]+|www\.[^\s]+')

def test_all_30_canonical_pairs():
    test_pairs_path = EXPANDED_DIR / "test_pairs.json"
    assert test_pairs_path.exists(), "test_pairs.json missing; generate expanded dataset first."

    with open(test_pairs_path, encoding="utf-8") as f:
        pairs = json.load(f)["pairs"]

    assert len(pairs) == 30, f"Expected 30 canonical test pairs, found {len(pairs)}"

    for pair in pairs:
        test_id = pair["test_id"]
        tid = pair["trigger_id"]
        mid = pair["merchant_id"]
        cid = pair.get("customer_id")

        with open(EXPANDED_DIR / "triggers" / f"{tid}.json", encoding="utf-8") as f:
            trigger = json.load(f)
        with open(EXPANDED_DIR / "merchants" / f"{mid}.json", encoding="utf-8") as f:
            merchant = json.load(f)
        cat_slug = merchant.get("category_slug", "dentists")
        with open(EXPANDED_DIR / "categories" / f"{cat_slug}.json", encoding="utf-8") as f:
            category = json.load(f)

        customer = None
        if cid:
            cust_file = EXPANDED_DIR / "customers" / f"{cid}.json"
            if cust_file.exists():
                with open(cust_file, encoding="utf-8") as f:
                    customer = json.load(f)

        result = compose(category, merchant, trigger, customer)

        # 1. Validate required keys
        for key in ["body", "cta", "send_as", "suppression_key", "rationale"]:
            assert key in result, f"[{test_id}] missing key {key}"
            assert result[key], f"[{test_id}] key {key} is empty"

        # 2. Validate send_as matches scope
        if trigger.get("scope") == "customer":
            assert result["send_as"] == "merchant_on_behalf", f"[{test_id}] expected merchant_on_behalf, got {result['send_as']}"
        else:
            assert result["send_as"] == "vera", f"[{test_id}] expected vera, got {result['send_as']}"

        # 3. Validate NO raw URLs
        assert not URL_REGEX.search(result["body"]), f"[{test_id}] URL found in message body: {result['body']}"

        # 4. Validate NO category taboo words
        taboos = category.get("voice", {}).get("vocab_taboo", [])
        for taboo in taboos:
            clean_taboo = re.sub(r'\(.*?\)', '', taboo).strip()
            if clean_taboo and len(clean_taboo) > 3:
                assert clean_taboo.lower() not in result["body"].lower(), f"[{test_id}] Taboo word '{clean_taboo}' found in body: {result['body']}"
