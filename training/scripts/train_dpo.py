import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig
from trl import DPOConfig, DPOTrainer


# ============================================================
# PATH
# ============================================================

MODEL_PATH = r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"

DATASET_PATH = r"C:\Project\ai\training\datasets\dpo_train.jsonl"

OUTPUT_DIR = r"C:\Project\ai\training\outputs\qwen2.5-0.5b-dpo-lora"


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

print(
    "Compute Capability:",
    f"{gpu.major}.{gpu.minor}",
)


# ============================================================
# TOKENIZER
# ============================================================

print()
print("=" * 70)
print("TOKENIZER")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

print("Tokenizer loaded.")


# ============================================================
# MODEL
# ============================================================

print()
print("=" * 70)
print("MODEL")
print("=" * 70)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float16,
    device_map="cuda",
    local_files_only=True,
)

model.config.use_cache = False

print("Model loaded.")


# ============================================================
# DATASET
# ============================================================

print()
print("=" * 70)
print("DPO DATASET")
print("=" * 70)

dataset = load_dataset(
    "json",
    data_files=DATASET_PATH,
    split="train",
)

print(dataset)
print("Samples:", len(dataset))

print()
print("First sample:")

print(dataset[0])


# ============================================================
# LORA
# ============================================================

print()
print("=" * 70)
print("LORA CONFIG")
print("=" * 70)

peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",

    # Sama seperti eksperimen QLoRA kita,
    # tetapi sekarang base model FP16.
    target_modules="all-linear",
)

print("Rank           :", 8)
print("Alpha          :", 16)
print("Dropout        :", 0.05)
print("Target modules :", "all-linear")


# ============================================================
# DPO CONFIG
# ============================================================

print()
print("=" * 70)
print("DPO CONFIG")
print("=" * 70)

training_args = DPOConfig(
    output_dir=OUTPUT_DIR,

    # Dataset
    max_length=512,

    # Batch
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,

    # Training
    num_train_epochs=3,

    # DPO normally uses a smaller learning rate
    # than LoRA SFT.
    learning_rate=5e-6,

    # GTX 1650:
    # avoid AMP/GradScaler because of the BF16
    # compatibility issue encountered earlier.
    fp16=False,
    bf16=False,

    # Disable clipping to avoid the GradScaler path
    # that caused the previous QLoRA error.
    max_grad_norm=0.0,

    gradient_checkpointing=True,

    # DPO beta controls the strength of the preference
    # objective.
    beta=0.1,

    # Logging
    logging_steps=1,
    report_to="none",

    # Saving
    save_strategy="epoch",
    save_total_limit=1,

    # Misc
    remove_unused_columns=False,
)


# ============================================================
# DPO TRAINER
# ============================================================

print()
print("=" * 70)
print("CREATING DPO TRAINER")
print("=" * 70)

trainer = DPOTrainer(
    model=model,

    args=training_args,

    train_dataset=dataset,

    processing_class=tokenizer,

    peft_config=peft_config,
)


# ============================================================
# TRAINABLE PARAMETER CHECK
# ============================================================

print()
print("=" * 70)
print("TRAINABLE PARAMETERS")
print("=" * 70)

total_parameters = 0
trainable_parameters = 0

for name, parameter in trainer.model.named_parameters():

    total_parameters += parameter.numel()

    if parameter.requires_grad:
        trainable_parameters += parameter.numel()


print(
    "Trainable parameters:",
    f"{trainable_parameters:,}",
)

print(
    "Total parameters:",
    f"{total_parameters:,}",
)

print(
    "Trainable percentage:",
    f"{100 * trainable_parameters / total_parameters:.4f}%",
)


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("START DPO TRAINING")
print("=" * 70)

result = trainer.train()


# ============================================================
# SAVE
# ============================================================

print()
print("=" * 70)
print("SAVING DPO ADAPTER")
print("=" * 70)

trainer.save_model(OUTPUT_DIR)

tokenizer.save_pretrained(OUTPUT_DIR)

print()
print("DPO training selesai.")
print("Output:", OUTPUT_DIR)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("TRAINING SUMMARY")
print("=" * 70)

print(result.metrics)