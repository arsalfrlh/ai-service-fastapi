import json
from pathlib import Path

DATASET_PATH = Path(
    r"C:\Project\ai\training\datasets\alpaca-id-cleaned\alpaca-id-cleaned.jsonl"
)

print("=" * 70)
print("INSPECT DATASET")
print("=" * 70)

with DATASET_PATH.open("r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Jumlah data : {len(lines)}")
print()

for i, line in enumerate(lines[:5]):
    item = json.loads(line)

    print(f"========== SAMPLE {i + 1} ==========")
    print("Keys:")
    print(item.keys())
    print()

    print("Instruction:")
    print(item.get("instruction"))

    print("\nInput:")
    print(item.get("input"))

    print("\nOutput:")
    print(item.get("output"))

    print()