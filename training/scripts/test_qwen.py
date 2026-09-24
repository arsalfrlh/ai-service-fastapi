import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_PATH = r".\models\Qwen2.5-0.5B-Instruct"

print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

print("Loading model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

print("Model loaded.")

messages = [
    {
        "role": "user",
        "content": "Jelaskan apa itu Laravel dalam satu paragraf."
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
        max_new_tokens=100,
        temperature=0.7,
        do_sample=True,
    )

generated_tokens = outputs[0][inputs["input_ids"].shape[-1]:]

response = tokenizer.decode(
    generated_tokens,
    skip_special_tokens=True,
)

print()
print("=" * 60)
print("QWEN RESPONSE")
print("=" * 60)
print(response)