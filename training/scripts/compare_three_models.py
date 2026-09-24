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

LORA_ADAPTER = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"
)

QLORA_ADAPTER = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-qlora"
)

TEST_DATASET = Path(
    r"C:\Project\ai\training\datasets\test_100.jsonl"
)

OUTPUT_FILE = Path(
    r"C:\Project\ai\training\outputs\comparison_three_models.jsonl"
)


# ============================================================
# SETTINGS
# ============================================================

# Untuk eksperimen pertama kita hanya menggunakan 20 data.
TEST_LIMIT = 20

MAX_NEW_TOKENS = 200

DO_SAMPLE = False

REPETITION_PENALTY = 1.05


# ============================================================
# DEVICE
# ============================================================

print("=" * 70)
print("DEVICE")
print("=" * 70)

if not torch.cuda.is_available():
    raise RuntimeError("CUDA tidak tersedia.")

print("CUDA :", torch.cuda.is_available())
print("GPU  :", torch.cuda.get_device_name(0))

gpu = torch.cuda.get_device_properties(0)

print(
    "VRAM :",
    round(gpu.total_memory / 1024**3, 2),
    "GB",
)


# ============================================================
# TOKENIZER
# ============================================================

print()
print("=" * 70)
print("LOADING TOKENIZER")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    BASE_MODEL,
    local_files_only=True,
)

print("Tokenizer loaded.")


# ============================================================
# LOAD ORIGINAL MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING ORIGINAL QWEN")
print("=" * 70)

original_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,

    dtype=torch.float16,

    device_map="cuda",

    local_files_only=True,
)

original_model.eval()

print("Original model loaded.")


# ============================================================
# LOAD LORA MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING LORA MODEL")
print("=" * 70)

lora_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,

    dtype=torch.float16,

    device_map="cuda",

    local_files_only=True,
)

lora_model = PeftModel.from_pretrained(
    lora_base,
    LORA_ADAPTER,
)

lora_model.eval()

print("LoRA model loaded.")


# ============================================================
# LOAD QLORA MODEL
# ============================================================

print()
print("=" * 70)
print("LOADING QLORA MODEL")
print("=" * 70)

# QLoRA adapter membutuhkan base model yang
# sama dengan base model saat training.
#
# Kita load base model dalam 4-bit agar penggunaan
# memory tetap konsisten dengan eksperimen QLoRA.

from transformers import BitsAndBytesConfig


bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,

    bnb_4bit_quant_type="nf4",

    bnb_4bit_compute_dtype=torch.float16,

    bnb_4bit_use_double_quant=True,
)


qlora_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,

    quantization_config=bnb_config,

    dtype=torch.float16,

    device_map="cuda",

    local_files_only=True,
)

qlora_model = PeftModel.from_pretrained(
    qlora_base,
    QLORA_ADAPTER,
)

qlora_model.eval()

print("QLoRA model loaded.")


# ============================================================
# LOAD TEST DATA
# ============================================================

print()
print("=" * 70)
print("LOADING TEST DATASET")
print("=" * 70)

with TEST_DATASET.open(
    "r",
    encoding="utf-8",
) as f:

    test_data = [
        json.loads(line)
        for line in f
    ]


test_data = test_data[:TEST_LIMIT]

print("Test samples:", len(test_data))


# ============================================================
# CREATE PROMPT
# ============================================================

def create_prompt(item):

    instruction = item.get(
        "instruction",
        "",
    ).strip()

    user_input = item.get(
        "input",
        "",
    ).strip()

    if user_input:

        return (
            f"{instruction}\n\n"
            f"Input:\n"
            f"{user_input}"
        )

    return instruction


# ============================================================
# GENERATE
# ============================================================

def generate(
    model,
    prompt: str,
):

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

            do_sample=DO_SAMPLE,

            repetition_penalty=REPETITION_PENALTY,
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

    prompt = create_prompt(item)

    reference = item.get(
        "output",
        "",
    ).strip()

    print()
    print("=" * 70)
    print(
        f"TEST {index + 1}/{len(test_data)}"
    )
    print("=" * 70)

    print()
    print("PROMPT:")
    print(prompt)

    print()
    print("-" * 70)
    print("ORIGINAL")
    print("-" * 70)

    original_response = generate(
        original_model,
        prompt,
    )

    print(original_response)

    print()
    print("-" * 70)
    print("LORA")
    print("-" * 70)

    lora_response = generate(
        lora_model,
        prompt,
    )

    print(lora_response)

    print()
    print("-" * 70)
    print("QLORA")
    print("-" * 70)

    qlora_response = generate(
        qlora_model,
        prompt,
    )

    print(qlora_response)

    print()
    print("-" * 70)
    print("REFERENCE")
    print("-" * 70)

    print(reference)

    # --------------------------------------------------------
    # SAVE RESULT
    # --------------------------------------------------------

    result = {
        "id": index,

        "instruction": item.get(
            "instruction",
            "",
        ),

        "input": item.get(
            "input",
            "",
        ),

        "reference": reference,

        "original": original_response,

        "lora": lora_response,

        "qlora": qlora_response,
    }

    results.append(result)


# ============================================================
# SAVE JSONL
# ============================================================

print()
print("=" * 70)
print("SAVING RESULTS")
print("=" * 70)

with OUTPUT_FILE.open(
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
print("Comparison selesai.")

print(
    "Saved:",
    OUTPUT_FILE,
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"Original : {len(results)} responses"
)

print(
    f"LoRA     : {len(results)} responses"
)

print(
    f"QLoRA    : {len(results)} responses"
)

print()
print("Output:")
print(OUTPUT_FILE)