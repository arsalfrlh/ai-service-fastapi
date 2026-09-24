import json
from pathlib import Path


SOURCE = Path(
    r"C:\Project\ai\training\datasets\alpaca-id-cleaned\alpaca-id-cleaned.jsonl"
)

OUTPUT = Path(
    r"C:\Project\ai\training\datasets\test_100.jsonl"
)

TRAIN_SIZE = 500
TEST_SIZE = 100


with SOURCE.open("r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]


test_data = data[TRAIN_SIZE:TRAIN_SIZE + TEST_SIZE]


with OUTPUT.open("w", encoding="utf-8") as f:
    for item in test_data:
        f.write(
            json.dumps(
                item,
                ensure_ascii=False
            )
            + "\n"
        )


print("=" * 60)
print("TEST DATASET")
print("=" * 60)

print("Total original :", len(data))
print("Train samples   :", TRAIN_SIZE)
print("Test samples    :", len(test_data))
print("Saved           :", OUTPUT)