import torch

from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


BASE_MODEL = r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"
ADAPTER = r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"


PROMPTS = [
    "Bagaimana cara menjaga kesehatan?",
    "Apa itu Laravel?",
    "Apa manfaat olahraga?",
    "Jelaskan apa itu Python.",
]


print("=" * 70)
print("LOADING TOKENIZER")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    local_files_only=True,
)


print("\n" + "=" * 70)
print("LOADING ORIGINAL MODEL")
print("=" * 70)

original_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

original_model.eval()


print("\n" + "=" * 70)
print("LOADING FINETUNED MODEL")
print("=" * 70)

finetuned_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

finetuned_model = PeftModel.from_pretrained(
    finetuned_base,
    ADAPTER,
)

finetuned_model.eval()


def generate(model, prompt):

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
            max_new_tokens=150,

            # Gunakan setting sama
            # untuk kedua model
            do_sample=False,

            repetition_penalty=1.05,
        )

    generated = outputs[0][inputs["input_ids"].shape[-1]:]

    return tokenizer.decode(
        generated,
        skip_special_tokens=True,
    )


for prompt in PROMPTS:

    print("\n")
    print("=" * 70)
    print("PROMPT")
    print("=" * 70)

    print(prompt)

    print("\n" + "-" * 70)
    print("ORIGINAL QWEN")
    print("-" * 70)

    original_response = generate(
        original_model,
        prompt,
    )

    print(original_response)

    print("\n" + "-" * 70)
    print("FINETUNED QWEN + LORA")
    print("-" * 70)

    finetuned_response = generate(
        finetuned_model,
        prompt,
    )

    print(finetuned_response)