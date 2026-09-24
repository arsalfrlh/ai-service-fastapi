import json
from pathlib import Path

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel


# ============================================================
# PATH
# ============================================================

BASE_MODEL = Path(
    r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"
)

SFT_ADAPTER = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"
)

DPO_ADAPTER = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-dpo-lora"
)

TEST_DATASET = Path(
    r"C:\Project\ai\training\datasets\dpo_test_20.jsonl"
)

OUTPUT_FILE = Path(
    r"C:\Project\ai\training\outputs\compare_sft_dpo_results.jsonl"
)


# ============================================================
# SETTINGS
# ============================================================

MAX_NEW_TOKENS = 160
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

print("CUDA :", True)
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
# LOAD ORIGINAL
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

print("Original loaded.")


# ============================================================
# LOAD SFT + LORA
# ============================================================

print()
print("=" * 70)
print("LOADING SFT + LORA")
print("=" * 70)

sft_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

sft_model = PeftModel.from_pretrained(
    sft_base,
    SFT_ADAPTER,
)

sft_model.eval()

print("SFT + LoRA loaded.")


# ============================================================
# LOAD DPO + LORA
# ============================================================

print()
print("=" * 70)
print("LOADING DPO + LORA")
print("=" * 70)

dpo_base = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

dpo_model = PeftModel.from_pretrained(
    dpo_base,
    DPO_ADAPTER,
)

dpo_model.eval()

print("DPO + LoRA loaded.")


# ============================================================
# LOAD TEST DATA
# ============================================================

print()
print("=" * 70)
print("LOADING DPO TEST DATASET")
print("=" * 70)

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
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=DO_SAMPLE,
            repetition_penalty=REPETITION_PENALTY,
        )

    generated = outputs[
        0
    ][
        inputs["input_ids"].shape[-1]:
    ]

    return tokenizer.decode(
        generated,
        skip_special_tokens=True,
    ).strip()


# ============================================================
# EVALUATION
# ============================================================

results = []

for index, item in enumerate(test_data):

    prompt = item["prompt"]
    chosen = item["chosen"]
    rejected = item["rejected"]

    print()
    print("=" * 70)
    print(f"TEST {index + 1}/{len(test_data)}")
    print("=" * 70)

    print("\nPROMPT:")
    print(prompt)

    print("\nGenerating ORIGINAL...")
    original = generate(
        original_model,
        prompt,
    )

    print("\nGenerating SFT + LORA...")
    sft = generate(
        sft_model,
        prompt,
    )

    print("\nGenerating DPO + LORA...")
    dpo = generate(
        dpo_model,
        prompt,
    )

    print("\n" + "-" * 70)
    print("ORIGINAL")
    print("-" * 70)
    print(original)

    print("\n" + "-" * 70)
    print("SFT + LORA")
    print("-" * 70)
    print(sft)

    print("\n" + "-" * 70)
    print("DPO + LORA")
    print("-" * 70)
    print(dpo)

    print("\n" + "-" * 70)
    print("PREFERRED / CHOSEN")
    print("-" * 70)
    print(chosen)

    result = {
        "id": item["id"],
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "original": original,
        "sft_lora": sft,
        "dpo_lora": dpo,
    }

    results.append(result)


# ============================================================
# SAVE
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

print("Saved:", OUTPUT_FILE)

print()
print("=" * 70)
print("EVALUATION COMPLETE")
print("=" * 70)