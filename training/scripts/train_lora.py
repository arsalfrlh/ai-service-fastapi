import torch

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


# ============================================================
# PATH
# ============================================================

MODEL_PATH = r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"

DATASET_PATH = r"C:\Project\ai\training\datasets\train_500_chat.jsonl"

OUTPUT_DIR = r"C:\Project\ai\training\outputs\qwen2.5-0.5b-lora"


# ============================================================
# DEVICE
# ============================================================

print("=" * 70)
print("DEVICE")
print("=" * 70)

print("CUDA available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print(
        "VRAM:",
        round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3,
            2,
        ),
        "GB",
    )


# ============================================================
# TOKENIZER
# ============================================================

print("\nLoading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)


# ============================================================
# MODEL
# ============================================================

print("Loading model...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)


# ============================================================
# DATASET
# ============================================================

print("Loading dataset...")

dataset = load_dataset(
    "json",
    data_files=DATASET_PATH,
    split="train",
)

print("Dataset:", dataset)
print("Samples:", len(dataset))

print("\nExample:")
print(dataset[0])


# ============================================================
# LORA CONFIG
# ============================================================

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",

    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
    ],
)


# ============================================================
# TRAINING CONFIG
# ============================================================

training_args = SFTConfig(
    output_dir=OUTPUT_DIR,

    # Dataset
    max_length=512,

    # Batch
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,

    # Epoch
    num_train_epochs=1,

    # Learning rate
    learning_rate=1e-4,

    # Optimization
    optim="adamw_torch",

    # Precision
    fp16=True,
    bf16=False,

    # Memory
    gradient_checkpointing=True,

    # Logging
    logging_steps=10,

    # Saving
    save_strategy="epoch",
    save_total_limit=2,

    # Reporting
    report_to="none",

    # Qwen EOS token
    eos_token="<|im_end|>",
)


# ============================================================
# TRAINER
# ============================================================

print("\nCreating trainer...")

trainer = SFTTrainer(
    model=model,
    args=training_args,

    train_dataset=dataset,

    processing_class=tokenizer,

    peft_config=lora_config,
)


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("START TRAINING")
print("=" * 70)

trainer.train()


# ============================================================
# SAVE
# ============================================================

print()
print("=" * 70)
print("SAVING MODEL")
print("=" * 70)

trainer.save_model(OUTPUT_DIR)

tokenizer.save_pretrained(OUTPUT_DIR)

print()
print("Training selesai.")
print("Output:", OUTPUT_DIR)