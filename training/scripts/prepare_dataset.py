import json
from pathlib import Path

SOURCE = Path(
    r"C:\Project\ai\training\datasets\alpaca-id-cleaned\alpaca-id-cleaned.jsonl"
)

OUTPUT = Path(
    r"C:\Project\ai\training\datasets\train_500.jsonl"
)

LIMIT = 500

with SOURCE.open("r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

data = data[:LIMIT]

with OUTPUT.open("w", encoding="utf-8") as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Dataset dibuat : {OUTPUT}")
print(f"Jumlah data    : {len(data)}")