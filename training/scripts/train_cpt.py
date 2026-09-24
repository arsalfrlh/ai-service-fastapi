import math
import torch

from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
)


# ============================================================
# PATH
# ============================================================

MODEL_PATH = (
    r"C:\Project\ai\training\models\Qwen2.5-0.5B"
)

DATASET_PATH = (
    r"C:\Project\ai\training\datasets\cpt_corpus.txt"
)

OUTPUT_DIR = (
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-cpt"
)


# ============================================================
# SETTINGS
# ============================================================

BLOCK_SIZE = 512


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
    dtype=torch.float32,
    device_map="cuda",
    local_files_only=True,
)

model.config.use_cache = False

print("Model loaded.")


# ============================================================
# LOAD RAW TEXT
# ============================================================

print()
print("=" * 70)
print("RAW TEXT DATASET")
print("=" * 70)

dataset = load_dataset(
    "text",
    data_files=DATASET_PATH,
)

print(dataset)


# ============================================================
# TOKENIZATION
# ============================================================

print()
print("=" * 70)
print("TOKENIZATION")
print("=" * 70)


def tokenize_function(examples):

    return tokenizer(
        examples["text"],
        add_special_tokens=False,
    )


tokenized = dataset.map(
    tokenize_function,
    batched=True,
    remove_columns=["text"],
)

print("Tokenization selesai.")


# ============================================================
# GROUP TOKENS
# ============================================================

print()
print("=" * 70)
print("GROUP TOKENS")
print("=" * 70)


def group_texts(examples):

    concatenated = {
        key: sum(examples[key], [])
        for key in examples.keys()
    }

    total_length = len(
        concatenated["input_ids"]
    )

    total_length = (
        total_length // BLOCK_SIZE
    ) * BLOCK_SIZE

    result = {
        key: [
            tokens[i:i + BLOCK_SIZE]
            for i in range(
                0,
                total_length,
                BLOCK_SIZE,
            )
        ]
        for key, tokens in concatenated.items()
    }

    result["labels"] = [
        chunk.copy()
        for chunk in result["input_ids"]
    ]

    return result


lm_dataset = tokenized.map(
    group_texts,
    batched=True,
)

print(lm_dataset)


# ============================================================
# TRAINING CONFIG
# ============================================================

print()
print("=" * 70)
print("TRAINING CONFIG")
print("=" * 70)

training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,

    # --------------------------------------------------------
    # Batch
    # --------------------------------------------------------

    per_device_train_batch_size=1,

    gradient_accumulation_steps=8,

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    num_train_epochs=1,

    learning_rate=5e-6,

    # --------------------------------------------------------
    # Precision
    # --------------------------------------------------------

    fp16=True,

    bf16=False,

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    gradient_checkpointing=True,

    # --------------------------------------------------------
    # Logging
    # --------------------------------------------------------

    logging_steps=1,

    report_to="none",

    # --------------------------------------------------------
    # Saving
    # --------------------------------------------------------

    save_strategy="epoch",

    save_total_limit=1,

    # --------------------------------------------------------
    # Optimizer
    # --------------------------------------------------------

    optim="adamw_torch",
)


# ============================================================
# TRAINER
# ============================================================

print()
print("=" * 70)
print("CREATING TRAINER")
print("=" * 70)

trainer = Trainer(
    model=model,

    args=training_args,

    train_dataset=lm_dataset["train"],
)


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("START CONTINUED PRETRAINING")
print("=" * 70)

result = trainer.train()


# ============================================================
# SAVE
# ============================================================

print()
print("=" * 70)
print("SAVING MODEL")
print("=" * 70)

trainer.save_model(
    OUTPUT_DIR
)

tokenizer.save_pretrained(
    OUTPUT_DIR
)

print()
print("Continued pretraining selesai.")

print(
    "Output:",
    OUTPUT_DIR,
)


# ============================================================
# METRICS
# ============================================================

print()
print("=" * 70)
print("METRICS")
print("=" * 70)

print(result.metrics)

if "train_loss" in result.metrics:

    try:

        perplexity = math.exp(
            result.metrics["train_loss"]
        )

        print(
            "Perplexity:",
            perplexity,
        )

    except OverflowError:

        print(
            "Perplexity terlalu besar."
        )