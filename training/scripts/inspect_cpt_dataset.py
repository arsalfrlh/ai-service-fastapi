from pathlib import Path

from transformers import AutoTokenizer


# ============================================================
# PATH
# ============================================================

MODEL_PATH = Path(
    r"C:\Project\ai\training\models\Qwen2.5-0.5B"
)

CORPUS_PATH = Path(
    r"C:\Project\ai\training\datasets\cpt_corpus.txt"
)


# ============================================================
# SETTINGS
# ============================================================

BLOCK_SIZE = 512


# ============================================================
# CHECK FILE
# ============================================================

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Model tidak ditemukan:\n{MODEL_PATH}"
    )

if not CORPUS_PATH.exists():
    raise FileNotFoundError(
        f"Corpus tidak ditemukan:\n{CORPUS_PATH}"
    )


# ============================================================
# LOAD RAW TEXT
# ============================================================

print("=" * 70)
print("CPT DATASET INSPECTION")
print("=" * 70)

text = CORPUS_PATH.read_text(
    encoding="utf-8"
)

print()
print("Corpus:")
print(CORPUS_PATH)

print()
print("Character count:")
print(len(text))

print()
print("Word count:")

words = text.split()

print(len(words))


# ============================================================
# TOKENIZER
# ============================================================

print()
print("=" * 70)
print("LOADING TOKENIZER")
print("=" * 70)

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    local_files_only=True,
)

print("Tokenizer loaded.")


# ============================================================
# TOKENIZE
# ============================================================

print()
print("=" * 70)
print("TOKENIZATION")
print("=" * 70)

encoded = tokenizer(
    text,
    add_special_tokens=False,
)

input_ids = encoded["input_ids"]

print()
print("Total tokens:")
print(len(input_ids))


# ============================================================
# TOKEN / WORD RATIO
# ============================================================

print()
print("=" * 70)
print("TOKEN STATISTICS")
print("=" * 70)

if len(words) > 0:

    tokens_per_word = (
        len(input_ids) / len(words)
    )

    print(
        "Tokens per word:",
        round(tokens_per_word, 3),
    )


# ============================================================
# BLOCK CALCULATION
# ============================================================

print()
print("=" * 70)
print("BLOCK CALCULATION")
print("=" * 70)

total_tokens = len(input_ids)

usable_tokens = (
    total_tokens // BLOCK_SIZE
) * BLOCK_SIZE

num_blocks = (
    usable_tokens // BLOCK_SIZE
)

discarded_tokens = (
    total_tokens - usable_tokens
)

print(
    "Block size:",
    BLOCK_SIZE,
)

print(
    "Usable tokens:",
    usable_tokens,
)

print(
    "Number of blocks:",
    num_blocks,
)

print(
    "Discarded tokens:",
    discarded_tokens,
)


# ============================================================
# SHOW FIRST TOKENS
# ============================================================

print()
print("=" * 70)
print("FIRST 50 TOKENS")
print("=" * 70)

first_tokens = input_ids[:50]

for index, token_id in enumerate(first_tokens):

    token_text = tokenizer.decode(
        [token_id]
    )

    print(
        f"{index:03d} | "
        f"ID: {token_id:>6} | "
        f"Token: {repr(token_text)}"
    )


# ============================================================
# SHOW FIRST BLOCK
# ============================================================

print()
print("=" * 70)
print("FIRST 512-TOKEN BLOCK")
print("=" * 70)

if num_blocks > 0:

    first_block = input_ids[
        :BLOCK_SIZE
    ]

    decoded_block = tokenizer.decode(
        first_block
    )

    print(decoded_block)

else:

    print(
        "Corpus belum memiliki 512 token."
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(
    f"Characters      : {len(text):,}"
)

print(
    f"Words           : {len(words):,}"
)

print(
    f"Tokens          : {total_tokens:,}"
)

print(
    f"Tokens/Word     : "
    f"{tokens_per_word:.3f}"
)

print(
    f"Block size      : {BLOCK_SIZE}"
)

print(
    f"Training blocks : {num_blocks:,}"
)

print(
    f"Discarded       : {discarded_tokens:,}"
)

print()
print("Inspection selesai.")