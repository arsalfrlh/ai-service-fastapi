import torch

from datasets import load_dataset

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    BitsAndBytesConfig,
)

from peft import (
    LoraConfig,
    prepare_model_for_kbit_training,
)

from trl import (
    SFTConfig,
    SFTTrainer,
)


# ============================================================
# PATH
# ============================================================

MODEL_PATH = r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"

DATASET_PATH = r"C:\Project\ai\training\datasets\train_500_chat.jsonl"

OUTPUT_DIR = r"C:\Project\ai\training\outputs\qwen2.5-0.5b-qlora"


# ============================================================
# DEVICE
# ============================================================

print("=" * 70)
print("DEVICE")
print("=" * 70)

if not torch.cuda.is_available():
    raise RuntimeError("CUDA tidak tersedia.")

gpu = torch.cuda.get_device_properties(0)

print("CUDA available :", torch.cuda.is_available())
print("GPU            :", torch.cuda.get_device_name(0))
print(
    "VRAM           :",
    round(gpu.total_memory / 1024**3, 2),
    "GB",
)
print(
    "Compute Cap.   :",
    f"{gpu.major}.{gpu.minor}",
)


# ============================================================
# PRECISION
# ============================================================

print()
print("=" * 70)
print("PRECISION")
print("=" * 70)

print(
    "BF16 supported:",
    torch.cuda.is_bf16_supported()
)

print("QLoRA compute dtype : float16")
print("Trainer AMP         : disabled")
print("Trainer BF16        : disabled")


# ============================================================
# BITSANDBYTES
# ============================================================

print()
print("=" * 70)
print("4-BIT CONFIG")
print("=" * 70)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,

    bnb_4bit_quant_type="nf4",

    bnb_4bit_compute_dtype=torch.float16,

    bnb_4bit_use_double_quant=True,
)

print("load_in_4bit        :", True)
print("quant_type          :", "nf4")
print("compute_dtype       :", "float16")
print("double_quantization :", True)


# ============================================================
# TOKENIZER
# ============================================================

print()
print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)


# ============================================================
# MODEL
# ============================================================

print("Loading Qwen 4-bit...")

model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,

    quantization_config=bnb_config,

    dtype=torch.float16,

    device_map="cuda",

    local_files_only=True,
)

model.config.use_cache = False

print("Model loaded.")

print(
    "First parameter dtype:",
    next(model.parameters()).dtype,
)


# ============================================================
# PREPARE K-BIT TRAINING
# ============================================================

print()
print("=" * 70)
print("PREPARE K-BIT TRAINING")
print("=" * 70)

model = prepare_model_for_kbit_training(
    model,
)

print("Model prepared.")


# ============================================================
# DATASET
# ============================================================

print()
print("=" * 70)
print("DATASET")
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

lora_config = LoraConfig(
    r=8,

    lora_alpha=16,

    lora_dropout=0.05,

    bias="none",

    task_type="CAUSAL_LM",

    target_modules="all-linear",
)

print("Rank           :", 8)
print("Alpha          :", 16)
print("Dropout        :", 0.05)
print("Target modules :", "all-linear")


# ============================================================
# TRAINING CONFIG
# ============================================================

print()
print("=" * 70)
print("TRAINING CONFIG")
print("=" * 70)

training_args = SFTConfig(

    output_dir=OUTPUT_DIR,

    max_length=512,

    per_device_train_batch_size=1,

    gradient_accumulation_steps=8,

    num_train_epochs=1,

    learning_rate=1e-4,

    # 8-bit optimizer
    optim="paged_adamw_8bit",

    # IMPORTANT
    # Disable AMP
    fp16=False,
    bf16=False,

    # Disable gradient clipping
    # so Accelerate does not invoke
    # the failing GradScaler path.
    max_grad_norm=0.0,

    gradient_checkpointing=True,

    logging_steps=10,

    report_to="none",

    save_strategy="epoch",

    save_total_limit=1,

    eos_token="<|im_end|>",
)


# ============================================================
# TRAINER
# ============================================================

print()
print("=" * 70)
print("CREATING TRAINER")
print("=" * 70)

trainer = SFTTrainer(

    model=model,

    args=training_args,

    train_dataset=dataset,

    processing_class=tokenizer,

    peft_config=lora_config,
)


# ============================================================
# FORCE TRAINABLE PARAMS TO FP32
# ============================================================

print()
print("=" * 70)
print("TRAINABLE PARAMETERS")
print("=" * 70)

total_parameters = 0
trainable_parameters = 0

dtype_counter = {}

for name, parameter in trainer.model.named_parameters():

    total_parameters += parameter.numel()

    if parameter.requires_grad:

        trainable_parameters += parameter.numel()

        # Force LoRA trainable tensors to FP32.
        parameter.data = parameter.data.float()

        dtype = str(parameter.dtype)

        dtype_counter[dtype] = (
            dtype_counter.get(dtype, 0) + 1
        )


print()
print("Trainable parameters:")
print(
    f"{trainable_parameters:,}"
)

print()
print("Total parameters:")
print(
    f"{total_parameters:,}"
)

print()
print("Trainable percentage:")
print(
    f"{100 * trainable_parameters / total_parameters:.4f}%"
)

print()
print("Trainable dtypes:")

for dtype, count in dtype_counter.items():

    print(
        f"{dtype}: {count}"
    )


# ============================================================
# TRAIN
# ============================================================

print()
print("=" * 70)
print("START QLORA TRAINING")
print("=" * 70)

trainer.train()


# ============================================================
# SAVE
# ============================================================

print()
print("=" * 70)
print("SAVING QLORA ADAPTER")
print("=" * 70)

trainer.save_model(
    OUTPUT_DIR
)

tokenizer.save_pretrained(
    OUTPUT_DIR
)

print()
print("Training selesai.")
print(
    "Output:",
    OUTPUT_DIR,
)


# ============================================================
# GPU MEMORY
# ============================================================

print()
print("=" * 70)
print("FINAL GPU MEMORY")
print("=" * 70)

allocated = (
    torch.cuda.memory_allocated() / 1024**3
)

reserved = (
    torch.cuda.memory_reserved() / 1024**3
)

print(
    f"Allocated : {allocated:.2f} GB"
)

print(
    f"Reserved  : {reserved:.2f} GB"
)