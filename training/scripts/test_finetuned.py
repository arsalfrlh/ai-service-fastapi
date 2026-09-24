import torch

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


BASE_MODEL = r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"

ADAPTER = r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"


print("=" * 70)
print("LOADING BASE MODEL")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    local_files_only=True,
)

base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

print("Base model loaded.")

print()
print("=" * 70)
print("LOADING LORA ADAPTER")
print("=" * 70)

model = PeftModel.from_pretrained(
    base_model,
    ADAPTER,
)

model.eval()

print("LoRA adapter loaded.")


def chat(prompt: str):
    messages = [
        {
            "role": "user",
            "content": prompt,
        }
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(model.device)
        for key, value in inputs.items()
    }

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=200,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )

    generated = outputs[0][inputs["input_ids"].shape[-1]:]

    return tokenizer.decode(
        generated,
        skip_special_tokens=True,
    )


print()
print("=" * 70)
print("FINETUNED QWEN")
print("=" * 70)

while True:

    prompt = input("\nYou: ")

    if prompt.lower() in {"exit", "quit"}:
        break

    response = chat(prompt)

    print("\nQwen:", response)