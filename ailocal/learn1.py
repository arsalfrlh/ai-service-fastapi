import torch
from transformers import AutoProcessor, AutoModelForMultimodalLM

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_PATH = r"C:\model\qwen"

MAX_NEW_TOKENS = 50
TOP_K = 10

# True  -> tampilkan informasi tensor/model secara detail
# False -> hanya tampilkan informasi penting
DEBUG = True

# ============================================================
# LOAD PROCESSOR
# ============================================================

print("=" * 90)
print("QWEN RAW INSPECTOR")
print("=" * 90)

print("\n[1] Loading processor...")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True
)

print("Processor loaded.")

# ============================================================
# LOAD MODEL
# ============================================================

print("\n[2] Loading model...")

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True
)

model.eval()

device = next(model.parameters()).device

print("Model loaded.")
print("Device :", device)
print("Dtype  :", next(model.parameters()).dtype)

# ============================================================
# MODEL INFORMATION
# ============================================================

print("\n[3] Model information")

try:
    total_parameters = sum(
        parameter.numel()
        for parameter in model.parameters()
    )

    print(
        "Parameters:",
        f"{total_parameters:,}"
    )

except Exception as e:
    print("Cannot calculate parameters:", e)

try:
    print(
        "Vocabulary:",
        model.config.vocab_size
    )
except Exception:
    print("Vocabulary: unknown")

try:
    print(
        "Hidden size:",
        model.config.hidden_size
    )
except Exception:
    print("Hidden size: unknown")

# ============================================================
# TOKENIZER INFORMATION
# ============================================================

tokenizer = processor.tokenizer

print("\n[4] Tokenizer information")

print("Tokenizer class:",
      tokenizer.__class__.__name__)

try:
    print("Vocabulary size:",
          len(tokenizer))
except Exception:
    pass

print("EOS token ID:",
      tokenizer.eos_token_id)

print("EOS token:",
      repr(tokenizer.eos_token))

print("PAD token ID:",
      tokenizer.pad_token_id)

print("PAD token:",
      repr(tokenizer.pad_token))

# ============================================================
# CONVERSATION HISTORY
# ============================================================

messages = []

# ============================================================
# HELPER FUNCTIONS
# ============================================================


def print_separator(title):
    print("\n")
    print("=" * 90)
    print(title)
    print("=" * 90)


def inspect_raw_prompt(messages):
    """
    Menampilkan chat template sebelum tokenisasi.
    """

    print_separator("RAW CHAT TEMPLATE")

    raw_prompt = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False
    )

    print(raw_prompt)

    return raw_prompt


def inspect_tokens(inputs):
    """
    Menampilkan token ID dan token satu per satu.
    """

    print_separator("TOKEN BREAKDOWN")

    input_ids = inputs["input_ids"][0]

    print("Total tokens:", len(input_ids))
    print()

    for position, token_id in enumerate(input_ids):

        token_id_int = token_id.item()

        token_text = tokenizer.decode(
            [token_id_int],
            skip_special_tokens=False
        )

        print(
            f"Position: {position:<5} "
            f"ID: {token_id_int:<8} "
            f"Token: {repr(token_text)}"
        )


def inspect_tensors(inputs):
    """
    Menampilkan informasi tensor.
    """

    print_separator("PYTORCH INPUT TENSORS")

    for key, value in inputs.items():

        if isinstance(value, torch.Tensor):

            print(f"\n[{key}]")

            print("  Shape :", tuple(value.shape))
            print("  Dtype :", value.dtype)
            print("  Device:", value.device)

            if DEBUG:
                try:
                    print(
                        "  Min   :",
                        value.min().item()
                    )

                    print(
                        "  Max   :",
                        value.max().item()
                    )
                except Exception:
                    pass


def inspect_model_parameters():
    """
    Menampilkan beberapa informasi parameter model.
    """

    print_separator("MODEL PARAMETERS")

    count = 0

    for name, parameter in model.named_parameters():

        print(
            f"{name:<70} "
            f"shape={tuple(parameter.shape)} "
            f"dtype={parameter.dtype}"
        )

        count += 1

        # Jangan memenuhi terminal.
        if count >= 20:
            print(
                "\n... only first 20 parameters displayed ..."
            )
            break


def inspect_logits(logits):
    """
    Menampilkan informasi logits mentah.
    """

    print_separator("RAW LOGITS")

    print("Logits shape :", tuple(logits.shape))
    print("Logits dtype :", logits.dtype)
    print("Logits device:", logits.device)

    print()

    print(
        "Min :",
        logits.min().item()
    )

    print(
        "Max :",
        logits.max().item()
    )

    print(
        "Mean:",
        logits.mean().item()
    )

    # Ambil logits pada posisi token terakhir.
    next_token_logits = logits[:, -1, :]

    print("\nNext-token logits shape:",
          tuple(next_token_logits.shape))

    return next_token_logits


def inspect_probabilities(next_token_logits):
    """
    Mengubah logits menjadi probability menggunakan softmax.
    """

    probabilities = torch.softmax(
        next_token_logits,
        dim=-1
    )

    print_separator("PROBABILITY DISTRIBUTION")

    print(
        "Probability shape:",
        tuple(probabilities.shape)
    )

    probability_sum = probabilities.sum().item()

    print(
        "Probability sum:",
        probability_sum
    )

    return probabilities


def inspect_top_k(probabilities, k=TOP_K):
    """
    Menampilkan kandidat token dengan probability terbesar.
    """

    print_separator(
        f"TOP {k} NEXT TOKEN CANDIDATES"
    )

    # probabilities memiliki shape:
    #
    # [batch, vocab_size]
    #
    # Ambil batch pertama.
    probs = probabilities[0]

    values, indices = torch.topk(
        probs,
        k
    )

    candidates = []

    for rank, (probability, token_id) in enumerate(
        zip(values, indices),
        start=1
    ):

        token_id_int = token_id.item()

        token_text = tokenizer.decode(
            [token_id_int],
            skip_special_tokens=False
        )

        percentage = probability.item() * 100

        print(
            f"{rank:>2}. "
            f"ID={token_id_int:<8} "
            f"Probability={percentage:>10.5f}% "
            f"Token={repr(token_text)}"
        )

        candidates.append(
            {
                "rank": rank,
                "token_id": token_id_int,
                "token": token_text,
                "probability": probability.item()
            }
        )

    return candidates


def select_greedy_token(next_token_logits):
    """
    Greedy decoding:
    memilih token dengan logit paling tinggi.
    """

    next_token_id = torch.argmax(
        next_token_logits,
        dim=-1,
        keepdim=True
    )

    token_id = next_token_id.item()

    token_text = tokenizer.decode(
        [token_id],
        skip_special_tokens=False
    )

    return next_token_id, token_text


def print_tensor_slice(tensor, name, count=20):
    """
    Menampilkan sebagian isi tensor saja.
    """

    print_separator(
        f"TENSOR SLICE: {name}"
    )

    flat = tensor.flatten()

    count = min(
        count,
        flat.numel()
    )

    print(
        flat[:count]
    )


def inspect_hidden_states(outputs):
    """
    Menampilkan hidden states jika tersedia.
    """

    hidden_states = getattr(
        outputs,
        "hidden_states",
        None
    )

    if hidden_states is None:
        print(
            "\nHidden states tidak tersedia."
        )
        return

    print_separator("HIDDEN STATES")

    print(
        "Jumlah hidden-state:",
        len(hidden_states)
    )

    for index, hidden_state in enumerate(
        hidden_states
    ):

        print(
            f"Layer {index:<4} "
            f"shape={tuple(hidden_state.shape)} "
            f"dtype={hidden_state.dtype}"
        )


def inspect_attentions(outputs):
    """
    Menampilkan attention jika tersedia.
    """

    attentions = getattr(
        outputs,
        "attentions",
        None
    )

    if attentions is None:
        print(
            "\nAttention tidak tersedia."
        )
        return

    print_separator("ATTENTION")

    print(
        "Jumlah attention layers:",
        len(attentions)
    )

    for index, attention in enumerate(
        attentions
    ):

        print(
            f"Layer {index:<4} "
            f"shape={tuple(attention.shape)}"
        )


def get_eos_ids():
    """
    Mengambil EOS token ID.
    Bisa berupa int atau list tergantung model.
    """

    eos_id = tokenizer.eos_token_id

    if eos_id is None:
        return set()

    if isinstance(eos_id, int):
        return {eos_id}

    return set(eos_id)


# ============================================================
# RAW GENERATION
# ============================================================


def raw_generate(inputs):
    """
    Generation loop manual.

    TIDAK menggunakan:
        model.generate()

    Kita sendiri yang:
        1. Forward pass
        2. Ambil logits
        3. Softmax
        4. Top-K
        5. Pilih token
        6. Tambahkan token
        7. Ulangi
    """

    print_separator("MANUAL AUTOREGRESSIVE GENERATION")

    generated_ids = inputs["input_ids"].clone()

    # Attention mask
    if "attention_mask" in inputs:
        attention_mask = inputs["attention_mask"].clone()
    else:
        attention_mask = torch.ones_like(
            generated_ids
        )

    eos_ids = get_eos_ids()

    generated_text = ""

    print("\nQwen: ", end="", flush=True)

    for step in range(MAX_NEW_TOKENS):

        print(
            f"\n\n--- GENERATION STEP {step + 1} ---"
        )

        # ====================================================
        # FORWARD PASS
        # ====================================================

        print("Running forward pass...")

        with torch.no_grad():

            outputs = model(
                input_ids=generated_ids,
                attention_mask=attention_mask,
                output_hidden_states=False,
                output_attentions=False,
                use_cache=False,
            )

        # ====================================================
        # LOGITS
        # ====================================================

        logits = outputs.logits

        print(
            "Logits shape:",
            tuple(logits.shape)
        )

        # ====================================================
        # LAST TOKEN LOGITS
        # ====================================================

        next_token_logits = logits[:, -1, :]

        print(
            "Next token logits shape:",
            tuple(next_token_logits.shape)
        )

        if DEBUG:

            print(
                "Logit min:",
                next_token_logits.min().item()
            )

            print(
                "Logit max:",
                next_token_logits.max().item()
            )

            print(
                "Logit mean:",
                next_token_logits.mean().item()
            )

        # ====================================================
        # SOFTMAX
        # ====================================================

        probabilities = torch.softmax(
            next_token_logits,
            dim=-1
        )

        # ====================================================
        # TOP-K
        # ====================================================

        top_values, top_indices = torch.topk(
            probabilities[0],
            TOP_K
        )

        print("\nTop candidates:")

        for rank, (
            probability,
            token_id
        ) in enumerate(
            zip(
                top_values,
                top_indices
            ),
            start=1
        ):

            token_id_int = token_id.item()

            token_text = tokenizer.decode(
                [token_id_int],
                skip_special_tokens=False
            )

            print(
                f"{rank:>2}. "
                f"ID={token_id_int:<8} "
                f"Probability="
                f"{probability.item() * 100:>9.4f}% "
                f"Token={repr(token_text)}"
            )

        # ====================================================
        # GREEDY SELECTION
        # ====================================================

        next_token_id, token_text = (
            select_greedy_token(
                next_token_logits
            )
        )

        token_id_int = next_token_id.item()

        print("\nSelected token:")
        print(
            "  ID   :",
            token_id_int
        )
        print(
            "  Text :",
            repr(token_text)
        )

        # ====================================================
        # PRINT TOKEN
        # ====================================================

        print(
            "\nGenerated: ",
            repr(token_text)
        )

        print(
            "Qwen: ",
            token_text,
            end="",
            flush=True
        )

        generated_text += token_text

        # ====================================================
        # EOS CHECK
        # ====================================================

        if token_id_int in eos_ids:

            print(
                "\n\nEOS token detected."
            )

            break

        # ====================================================
        # APPEND TOKEN
        # ====================================================

        generated_ids = torch.cat(
            [
                generated_ids,
                next_token_id
            ],
            dim=-1
        )

        # ====================================================
        # UPDATE ATTENTION MASK
        # ====================================================

        new_attention = torch.ones(
            (
                attention_mask.shape[0],
                1
            ),
            dtype=attention_mask.dtype,
            device=attention_mask.device
        )

        attention_mask = torch.cat(
            [
                attention_mask,
                new_attention
            ],
            dim=-1
        )

        print(
            "\nCurrent sequence length:",
            generated_ids.shape[-1]
        )

    print("\n\n")
    print(
        "=" * 90
    )

    print(
        "FINAL GENERATED TEXT"
    )

    print(
        "=" * 90
    )

    print(generated_text)

    print(
        "=" * 90
    )

    return generated_text


# ============================================================
# MAIN CHAT LOOP
# ============================================================

print("\n")
print("=" * 90)
print("QWEN RAW INSPECTOR READY")
print("=" * 90)

print(
    "\nCommands:"
)

print(
    "  quit  -> keluar"
)

print(
    "  clear -> hapus conversation history"
)

print(
    "  params -> lihat parameter model"
)

print(
    "\nSetiap pertanyaan akan diperiksa secara bertahap."
)

# ============================================================

while True:

    try:

        user_input = input(
            "\nAnda: "
        ).strip()

    except KeyboardInterrupt:

        print(
            "\n\nProgram dihentikan."
        )

        break

    except EOFError:

        print(
            "\n\nProgram dihentikan."
        )

        break

    # ========================================================
    # COMMANDS
    # ========================================================

    if user_input.lower() in {
        "quit",
        "exit"
    }:

        break

    if user_input.lower() == "clear":

        messages.clear()

        print(
            "\nConversation history cleared."
        )

        continue

    if user_input.lower() == "params":

        inspect_model_parameters()

        continue

    if not user_input:

        continue

    # ========================================================
    # ADD USER MESSAGE
    # ========================================================

    messages.append(
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": user_input
                }
            ]
        }
    )

    # ========================================================
    # RAW CHAT TEMPLATE
    # ========================================================

    raw_prompt = inspect_raw_prompt(
        messages
    )

    # ========================================================
    # TOKENIZATION
    # ========================================================

    print_separator("TOKENIZATION")

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    # ========================================================
    # MOVE TO MODEL DEVICE
    # ========================================================

    inputs = inputs.to(
        model.device
    )

    print(
        "Input moved to:",
        model.device
    )

    # ========================================================
    # INSPECT TENSORS
    # ========================================================

    inspect_tensors(
        inputs
    )

    # ========================================================
    # INSPECT TOKENS
    # ========================================================

    inspect_tokens(
        inputs
    )

    # ========================================================
    # FIRST FORWARD PASS
    # ========================================================

    print_separator(
        "FIRST MODEL FORWARD PASS"
    )

    print(
        "Running model..."
    )

    with torch.no_grad():

        outputs = model(
            **inputs,
            output_hidden_states=False,
            output_attentions=False,
            use_cache=False,
        )

    print(
        "Forward pass completed."
    )

    # ========================================================
    # MODEL OUTPUT INFO
    # ========================================================

    print(
        "\nOutput object:",
        type(outputs)
    )

    try:

        print(
            "Output fields:",
            outputs.keys()
        )

    except Exception:

        pass

    # ========================================================
    # LOGITS
    # ========================================================

    logits = outputs.logits

    next_token_logits = inspect_logits(
        logits
    )

    # ========================================================
    # LOGITS SAMPLE
    # ========================================================

    if DEBUG:

        print_tensor_slice(
            next_token_logits,
            "NEXT TOKEN LOGITS",
            20
        )

    # ========================================================
    # PROBABILITY
    # ========================================================

    probabilities = inspect_probabilities(
        next_token_logits
    )

    # ========================================================
    # TOP K
    # ========================================================

    inspect_top_k(
        probabilities,
        TOP_K
    )

    # ========================================================
    # SELECT TOKEN
    # ========================================================

    next_token_id, selected_token = (
        select_greedy_token(
            next_token_logits
        )
    )

    print_separator(
        "FIRST SELECTED TOKEN"
    )

    print(
        "Token ID:",
        next_token_id.item()
    )

    print(
        "Token:",
        repr(selected_token)
    )

    # ========================================================
    # MANUAL GENERATION
    # ========================================================

    response = raw_generate(
        inputs
    )

    # ========================================================
    # ADD ASSISTANT RESPONSE
    # ========================================================

    messages.append(
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response
                }
            ]
        }
    )

    print(
        "\nConversation history:",
        len(messages),
        "messages"
    )


# ==========================================================================================
# QWEN RAW INSPECTOR
# ==========================================================================================

# [1] Loading processor...
# Processor loaded.

# [2] Loading model...
# Loading weights: 100%|██████████████████████████████████████████████████████████████| 473/473 [00:00<00:00, 1277.49it/s]
# Model loaded.
# Device : cpu
# Dtype  : torch.float32

# [3] Model information
# Parameters: 852,985,920
# Vocabulary: unknown
# Hidden size: unknown

# [4] Tokenizer information
# Tokenizer class: Qwen2Tokenizer
# Vocabulary size: 248077
# EOS token ID: 248046
# EOS token: '<|im_end|>'
# PAD token ID: 248044
# PAD token: '<|endoftext|>'

# ==========================================================================================
# QWEN RAW INSPECTOR READY
# ==========================================================================================

# Commands:
#   quit  -> keluar
#   clear -> hapus conversation history
#   params -> lihat parameter model

# Setiap pertanyaan akan diperiksa secara bertahap.

# Anda: Who are you?


# ==========================================================================================
# RAW CHAT TEMPLATE
# ==========================================================================================
# <|im_start|>user
# Who are you?<|im_end|>
# <|im_start|>assistant
# <think>

# </think>


# ==========================================================================================
# TOKENIZATION
# ==========================================================================================
# Input moved to: cpu


# ==========================================================================================
# PYTORCH INPUT TENSORS
# ==========================================================================================

# [input_ids]
#   Shape : (1, 16)
#   Dtype : torch.int64
#   Device: cpu
#   Min   : 30
#   Max   : 248069

# [attention_mask]
#   Shape : (1, 16)
#   Dtype : torch.int64
#   Device: cpu
#   Min   : 1
#   Max   : 1

# [mm_token_type_ids]
#   Shape : (1, 16)
#   Dtype : torch.int64
#   Device: cpu
#   Min   : 0
#   Max   : 0


# ==========================================================================================
# TOKEN BREAKDOWN
# ==========================================================================================
# Total tokens: 16

# Position: 0     ID: 248045   Token: '<|im_start|>'
# Position: 1     ID: 846      Token: 'user'
# Position: 2     ID: 198      Token: '\n'
# Position: 3     ID: 14749    Token: 'Who'
# Position: 4     ID: 513      Token: ' are'
# Position: 5     ID: 488      Token: ' you'
# Position: 6     ID: 30       Token: '?'
# Position: 7     ID: 248046   Token: '<|im_end|>'
# Position: 8     ID: 198      Token: '\n'
# Position: 9     ID: 248045   Token: '<|im_start|>'
# Position: 10    ID: 74455    Token: 'assistant'
# Position: 11    ID: 198      Token: '\n'
# Position: 12    ID: 248068   Token: '<think>'
# Position: 13    ID: 271      Token: '\n\n'
# Position: 14    ID: 248069   Token: '</think>'
# Position: 15    ID: 271      Token: '\n\n'


# ==========================================================================================
# FIRST MODEL FORWARD PASS
# ==========================================================================================
# Running model...
# Forward pass completed.

# Output object: <class 'transformers.models.qwen3_5.modeling_qwen3_5.Qwen3_5CausalLMOutputWithPast'>
# Output fields: odict_keys(['logits'])


# ==========================================================================================
# RAW LOGITS
# ==========================================================================================
# Logits shape : (1, 16, 248320)
# Logits dtype : torch.float32
# Logits device: cpu

# Min : -16.636192321777344
# Max : 30.153400421142578
# Mean: -1.609890341758728

# Next-token logits shape: (1, 248320)


# ==========================================================================================
# TENSOR SLICE: NEXT TOKEN LOGITS
# ==========================================================================================
# tensor([13.6866, 15.7619, 11.2397,  8.0632,  8.1110,  7.0970, 10.8116, 10.1688,
#          6.1151, 15.3546, 11.3078,  5.1340, 10.9774,  7.1620,  9.8053,  8.4316,
#         12.9512, 10.9369,  7.8832,  7.4292])


# ==========================================================================================
# PROBABILITY DISTRIBUTION
# ==========================================================================================
# Probability shape: (1, 248320)
# Probability sum: 1.0000213384628296


# ==========================================================================================
# TOP 10 NEXT TOKEN CANDIDATES
# ==========================================================================================
#  1. ID=40       Probability=  69.56366% Token='I'
#  2. ID=9419     Probability=  21.31460% Token='Hello'
#  3. ID=2053     Probability=   4.64587% Token='As'
#  4. ID=332      Probability=   1.19853% Token='**'
#  5. ID=12675    Probability=   0.98151% Token='Hi'
#  6. ID=14749    Probability=   0.33112% Token='Who'
#  7. ID=18103    Probability=   0.21892% Token='Hey'
#  8. ID=4888     Probability=   0.11726% Token='My'
#  9. ID=23982    Probability=   0.09824% Token='Ah'
# 10. ID=88621    Probability=   0.09576% Token='Greetings'


# ==========================================================================================
# FIRST SELECTED TOKEN
# ==========================================================================================
# Token ID: 40
# Token: 'I'


# ==========================================================================================
# MANUAL AUTOREGRESSIVE GENERATION
# ==========================================================================================

# Qwen: 

# --- GENERATION STEP 1 ---
# Running forward pass...
# Logits shape: (1, 16, 248320)
# Next token logits shape: (1, 248320)
# Logit min: -10.785355567932129
# Logit max: 23.266101837158203
# Logit mean: -0.8895506262779236

# Top candidates:
#  1. ID=40       Probability=  69.5637% Token='I'
#  2. ID=9419     Probability=  21.3146% Token='Hello'
#  3. ID=2053     Probability=   4.6459% Token='As'
#  4. ID=332      Probability=   1.1985% Token='**'
#  5. ID=12675    Probability=   0.9815% Token='Hi'
#  6. ID=14749    Probability=   0.3311% Token='Who'
#  7. ID=18103    Probability=   0.2189% Token='Hey'
#  8. ID=4888     Probability=   0.1173% Token='My'
#  9. ID=23982    Probability=   0.0982% Token='Ah'
# 10. ID=88621    Probability=   0.0958% Token='Greetings'

# Selected token:
#   ID   : 40
#   Text : 'I'

# Generated:  'I'
# Qwen:  I
# Current sequence length: 17


# --- GENERATION STEP 2 ---
# Running forward pass...
# Logits shape: (1, 17, 248320)
# Next token logits shape: (1, 248320)
# Logit min: -14.769176483154297
# Logit max: 22.25841522216797
# Logit mean: -3.1607542037963867

# Top candidates:
#  1. ID=1044     Probability=  67.5005% Token=' am'
#  2. ID=2688     Probability=  30.8054% Token="'m"
#  3. ID=1459     Probability=   1.1335% Token=' don'
#  4. ID=4110     Probability=   0.0786% Token='’m'
#  5. ID=628      Probability=   0.0668% Token=' can'
#  6. ID=2972     Probability=   0.0641% Token=' **'
#  7. ID=1366     Probability=   0.0501% Token=' know'
#  8. ID=2905     Probability=   0.0167% Token=' exist'
#  9. ID=4021     Probability=   0.0148% Token=' cannot'
# 10. ID=369      Probability=   0.0148% Token=' is'

# Selected token:
#   ID   : 1044
#   Text : ' am'

# Generated:  ' am'
# Qwen:   am
# Current sequence length: 18


# --- GENERATION STEP 3 ---
# Running forward pass...
# Logits shape: (1, 18, 248320)
# Next token logits shape: (1, 248320)
# Logit min: -14.86294937133789
# Logit max: 20.52466583251953
# Logit mean: -3.6891870498657227

# Top candidates:
#  1. ID=1167     Probability=  89.9752% Token=' Q'
#  2. ID=2972     Probability=   9.0648% Token=' **'
#  3. ID=449      Probability=   0.3680% Token=' an'
#  4. ID=264      Probability=   0.3129% Token=' a'
#  5. ID=48       Probability=   0.0254% Token='Q'
#  6. ID=3297     Probability=   0.0247% Token=' Qu'
#  7. ID=279      Probability=   0.0159% Token=' the'
#  8. ID=52540    Probability=   0.0113% Token=' Alibaba'
#  9. ID=7309     Probability=   0.0094% Token=' highly'
# 10. ID=524      Probability=   0.0088% Token=' not'

# Selected token:
#   ID   : 1167
#   Text : ' Q'

# Generated:  ' Q'
# Qwen:   Q
# Current sequence length: 19


# --- GENERATION STEP 4 ---
# Running forward pass...
# Logits shape: (1, 19, 248320)
# Next token logits shape: (1, 248320)
# Logit min: -15.622305870056152
# Logit max: 23.122013092041016
# Logit mean: -2.9398136138916016

# Top candidates:
#  1. ID=16451    Probability=  99.8070% Token='wen'
#  2. ID=18       Probability=   0.1480% Token='3'
#  3. ID=1068     Probability=   0.0147% Token='ian'
#  4. ID=11       Probability=   0.0070% Token=','
#  5. ID=2014     Probability=   0.0027% Token='An'
#  6. ID=19       Probability=   0.0015% Token='4'
#  7. ID=54       Probability=   0.0010% Token='W'
#  8. ID=59157    Probability=   0.0008% Token=' Wen'
#  9. ID=35695    Probability=   0.0007% Token='WN'
# 10. ID=18313    Probability=   0.0007% Token='-an'

# Selected token:
#   ID   : 16451
#   Text : 'wen'

# Generated:  'wen'
# Qwen:  wen
# Current sequence length: 20


# --- GENERATION STEP 5 ---
# Running forward pass...
# Logits shape: (1, 20, 248320)
# Next token logits shape: (1, 248320)
# Logit min: -15.20979118347168
# Logit max: 25.381023406982422
# Logit mean: -3.9059500694274902

# Top candidates:
#  1. ID=18       Probability=  99.9314% Token='3'
#  2. ID=11       Probability=   0.0634% Token=','
#  3. ID=15428    Probability=   0.0013% Token='�'
#  4. ID=220      Probability=   0.0005% Token=' '
#  5. ID=14016    Probability=   0.0004% Token=' III'
#  6. ID=19       Probability=   0.0003% Token='4'
#  7. ID=17       Probability=   0.0003% Token='2'
#  8. ID=3709     Probability=   0.0002% Token='，'
#  9. ID=5084     Probability=   0.0002% Token='-M'
# 10. ID=32405    Probability=   0.0002% Token='３'

# Selected token:
#   ID   : 18
#   Text : '3'

# Generated:  '3'
# Qwen:  3
# Current sequence length: 21


# --- GENERATION STEP 6 ---
# Running forward pass...

# Selected token:
#   ID   : 3242
#   Text : ' today'

# Generated:  ' today'
# Qwen:   today
# Current sequence length: 66



# ==========================================================================================
# FINAL GENERATED TEXT
# ==========================================================================================
# I am Qwen3.5, the latest large language model developed by Tongyi Lab. I am designed to assist you with a wide range of tasks, including answering questions, writing stories, coding, and more. How can I help you today
# ==========================================================================================

# Conversation history: 2 messages

# Anda: 