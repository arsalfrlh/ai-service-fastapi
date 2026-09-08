import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM

MODEL_PATH=r"C:\model\qwen"
print("Loading Process...")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True
)

print("Loading model...")

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True
)

model.eval()

print("\nModel berhasil dimuat!")
print("Device:", next(model.parameters()).device)
print("Ketik 'exit' untuk keluar.\n")

messages = []

while True:
    user_input = input("Anda: ")

    if user_input.lower() == "quit":
        break

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_input
            }
        ]
    })

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = inputs.to(model.device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=256,
        )

    input_length = inputs["input_ids"].shape[-1]

    generated_tokens = outputs[
        0,
        input_length:
    ]

    response = processor.decode(
        generated_tokens,
        skip_special_tokens=True,
    )

    print(f"Qwen: {response}\n")

    messages.append({
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": response,
            }
        ],
    })