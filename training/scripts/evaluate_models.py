import json
from pathlib import Path

import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)

from peft import PeftModel


# ============================================================
# PATH
# ============================================================

BASE_MODEL = Path(
    r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"
)

ADAPTER = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"
)

TEST_DATASET = Path(
    r"C:\Project\ai\training\datasets\test_100.jsonl"
)

OUTPUT = Path(
    r"C:\Project\ai\training\outputs\evaluation_results.jsonl"
)


# ============================================================
# SETTINGS
# ============================================================

MAX_NEW_TOKENS = 150


# ============================================================
# DEVICE
# ============================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


print("=" * 70)
print("DEVICE")
print("=" * 70)

print("Device:", DEVICE)

if torch.cuda.is_available():

    print(
        "GPU:",
        torch.cuda.get_device_name(0)
    )


# ============================================================
# TOKENIZER
# ============================================================

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    local_files_only=True,
)


# ============================================================
# ORIGINAL MODEL
# ============================================================

print("\nLoading original Qwen...")

original_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

original_model.eval()


# ============================================================
# FINETUNED MODEL
# ============================================================

print("\nLoading fine-tuned Qwen...")

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


# ============================================================
# LOAD TEST DATA
# ============================================================

print("\nLoading test dataset...")

with TEST_DATASET.open(
    "r",
    encoding="utf-8",
) as f:

    test_data = [
        json.loads(line)
        for line in f
    ]


print("Test samples:", len(test_data))


# ============================================================
# GENERATE
# ============================================================

def generate(
    model,
    prompt: str,
) -> str:

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

            max_new_tokens=MAX_NEW_TOKENS,

            do_sample=False,

            repetition_penalty=1.05,
        )

    generated = outputs[
        0
    ][
        inputs["input_ids"].shape[-1]:
    ]

    response = tokenizer.decode(
        generated,
        skip_special_tokens=True,
    )

    return response.strip()


# ============================================================
# EVALUATION
# ============================================================

results = []


for index, item in enumerate(test_data):

    instruction = item.get(
        "instruction",
        "",
    ).strip()

    user_input = item.get(
        "input",
        "",
    ).strip()

    reference = item.get(
        "output",
        "",
    ).strip()


    if user_input:

        prompt = (
            f"{instruction}\n\n"
            f"Input:\n"
            f"{user_input}"
        )

    else:

        prompt = instruction


    print()
    print("=" * 70)
    print(
        f"TEST {index + 1}/{len(test_data)}"
    )
    print("=" * 70)

    print("Prompt:")
    print(prompt)


    # --------------------------------------------------------
    # ORIGINAL
    # --------------------------------------------------------

    print("\nGenerating ORIGINAL...")

    original_response = generate(
        original_model,
        prompt,
    )


    # --------------------------------------------------------
    # FINETUNED
    # --------------------------------------------------------

    print("Generating FINETUNED...")

    finetuned_response = generate(
        finetuned_model,
        prompt,
    )


    # --------------------------------------------------------
    # STORE
    # --------------------------------------------------------

    result = {

        "id": index,

        "instruction": instruction,

        "input": user_input,

        "reference": reference,

        "original": original_response,

        "finetuned": finetuned_response,
    }


    results.append(result)


    print("\nREFERENCE:")
    print(reference)

    print("\nORIGINAL:")
    print(original_response)

    print("\nFINETUNED:")
    print(finetuned_response)


# ============================================================
# SAVE
# ============================================================

with OUTPUT.open(
    "w",
    encoding="utf-8",
) as f:

    for result in results:

        f.write(
            json.dumps(
                result,
                ensure_ascii=False,
            )
            + "\n"
        )


print()
print("=" * 70)
print("EVALUATION COMPLETE")
print("=" * 70)

print(
    "Saved:",
    OUTPUT
)