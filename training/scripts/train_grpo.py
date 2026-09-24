import re
from pathlib import Path

import torch

from datasets import load_dataset

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
)

from peft import LoraConfig

from trl import (
    GRPOConfig,
    GRPOTrainer,
)


# ============================================================
# PATH
# ============================================================

MODEL_PATH = Path(
    r"C:\Project\ai\training\models\Qwen2.5-0.5B-Instruct"
)

DATASET_PATH = Path(
    r"C:\Project\ai\training\datasets\grpo_math_20.jsonl"
)

OUTPUT_DIR = Path(
    r"C:\Project\ai\training\outputs\qwen2.5-0.5b-grpo-lora"
)


# ============================================================
# SETTINGS
# ============================================================

MAX_PROMPT_LENGTH = 128

MAX_COMPLETION_LENGTH = 64

NUM_GENERATIONS = 2


# ============================================================
# DEVICE
# ============================================================

print("=" * 70)
print("DEVICE")
print("=" * 70)

if not torch.cuda.is_available():
    raise RuntimeError(
        "CUDA tidak tersedia."
    )

print(
    "CUDA :",
    torch.cuda.is_available(),
)

print(
    "GPU  :",
    torch.cuda.get_device_name(0),
)

gpu = torch.cuda.get_device_properties(0)

print(
    "VRAM :",
    round(
        gpu.total_memory / 1024**3,
        2,
    ),
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
print("GRPO DATASET")
print("=" * 70)

dataset = load_dataset(
    "json",
    data_files=str(DATASET_PATH),
    split="train",
)

print(dataset)

print(
    "Samples:",
    len(dataset),
)

print()
print(
    "First sample:"
)

print(
    dataset[0]
)


# ============================================================
# REWARD FUNCTION
# ============================================================

def extract_number(text: str):

    """
    Mengambil angka terakhir dari output model.

    Contoh:

        "56"
        -> 56

        "Jawabannya adalah 56."
        -> 56

        "Hasilnya = 42"
        -> 42
    """

    matches = re.findall(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not matches:
        return None

    return matches[-1]


def math_reward(
    prompts,
    completions,
    answer,
    **kwargs,
):
    rewards = []

    for prompt, completion, expected in zip(
        prompts,
        completions,
        answer,
    ):

        # ----------------------------------------------------
        # Extract completion text
        # ----------------------------------------------------

        if isinstance(completion, list):

            text = ""

            for item in completion:

                if isinstance(item, dict):

                    text += str(
                        item.get(
                            "content",
                            "",
                        )
                    )

                else:

                    text += str(item)

        else:

            text = str(completion)


        # ----------------------------------------------------
        # Extract predicted number
        # ----------------------------------------------------

        predicted = extract_number(
            text
        )

        expected = str(
            expected
        ).strip()


        # ----------------------------------------------------
        # Reward
        # ----------------------------------------------------

        if predicted == expected:

            reward = 1.0

        else:

            reward = 0.0


        rewards.append(reward)


        # ----------------------------------------------------
        # Print reward
        # ----------------------------------------------------

        print()
        print("-" * 60)
        print("REWARD CHECK")
        print("-" * 60)

        print("Prompt   :", prompt)
        print("Output   :", text)
        print("Expected :", expected)
        print("Predicted:", predicted)
        print("Reward   :", reward)


    return rewards


# ============================================================
# LORA CONFIG
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

    target_modules="all-linear",
)

print(
    "Rank:",
    8,
)

print(
    "Alpha:",
    16,
)

print(
    "Dropout:",
    0.05,
)

print(
    "Target modules:",
    "all-linear",
)


# ============================================================
# GRPO CONFIG
# ============================================================

print()
print("=" * 70)
print("GRPO CONFIG")
print("=" * 70)

training_args = GRPOConfig(

    output_dir=str(
        OUTPUT_DIR
    ),

    # --------------------------------------------------------
    # Generation
    # --------------------------------------------------------

    num_generations=NUM_GENERATIONS,

    # max_completion_length=MAX_COMPLETION_LENGTH,
    max_completion_length=64,

    # max_prompt_length=MAX_PROMPT_LENGTH,

    # --------------------------------------------------------
    # Batch
    # --------------------------------------------------------

    per_device_train_batch_size=2,
    # per_device_train_batch_size=1,

    gradient_accumulation_steps=1,

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    num_train_epochs=1,

    learning_rate=5e-6,

    # --------------------------------------------------------
    # Precision
    # --------------------------------------------------------

    fp16=False,

    bf16=False,

    # --------------------------------------------------------
    # Gradient
    # --------------------------------------------------------

    max_grad_norm=0.0,

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
    # GRPO
    # --------------------------------------------------------

    beta=0.1,

)


print(
    "Generations per prompt:",
    NUM_GENERATIONS,
)

print(
    "Epochs:",
    1,
)

print(
    "Learning rate:",
    5e-6,
)

print(
    "Max completion:",
    MAX_COMPLETION_LENGTH,
)


# ============================================================
# GRPO TRAINER
# ============================================================

print()
print("=" * 70)
print("CREATING GRPO TRAINER")
print("=" * 70)

trainer = GRPOTrainer(

    model=model,

    args=training_args,

    train_dataset=dataset,

    processing_class=tokenizer,

    reward_funcs=math_reward,

    peft_config=peft_config,
)


# ============================================================
# TRAINABLE PARAMETERS
# ============================================================

print()
print("=" * 70)
print("TRAINABLE PARAMETERS")
print("=" * 70)

total_parameters = 0

trainable_parameters = 0


for name, parameter in (
    trainer.model.named_parameters()
):

    total_parameters += (
        parameter.numel()
    )

    if parameter.requires_grad:

        trainable_parameters += (
            parameter.numel()
        )


print(
    "Trainable:",
    f"{trainable_parameters:,}",
)

print(
    "Total:",
    f"{total_parameters:,}",
)

print(
    "Trainable percentage:",
    f"{100 * trainable_parameters / total_parameters:.4f}%",
)


# ============================================================
# START TRAINING
# ============================================================

print()
print("=" * 70)
print("START GRPO TRAINING")
print("=" * 70)

result = trainer.train()


# ============================================================
# SAVE
# ============================================================

print()
print("=" * 70)
print("SAVING GRPO ADAPTER")
print("=" * 70)

trainer.save_model(
    str(OUTPUT_DIR)
)

tokenizer.save_pretrained(
    str(OUTPUT_DIR)
)

print()
print(
    "GRPO training selesai."
)

print(
    "Output:",
    OUTPUT_DIR,
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("TRAINING SUMMARY")
print("=" * 70)

print(
    result.metrics
)