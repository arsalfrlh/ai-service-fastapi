import json
from pathlib import Path

SOURCE = Path(
    r"C:\Project\ai\training\datasets\train_500.jsonl"
)

OUTPUT = Path(
    r"C:\Project\ai\training\datasets\train_500_chat.jsonl"
)


def convert(item):
    instruction = item.get("instruction", "").strip()
    user_input = item.get("input", "").strip()
    output = item.get("output", "").strip()

    if user_input:
        user_content = f"{instruction}\n\nInput:\n{user_input}"
    else:
        user_content = instruction

    return {
        "messages": [
            {
                "role": "user",
                "content": user_content,
            },
            {
                "role": "assistant",
                "content": output,
            },
        ]
    }


with SOURCE.open("r", encoding="utf-8") as f:
    data = [json.loads(line) for line in f]

converted = [convert(item) for item in data]

with OUTPUT.open("w", encoding="utf-8") as f:
    for item in converted:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"Input  : {len(data)}")
print(f"Output : {len(converted)}")
print(f"Saved  : {OUTPUT}")