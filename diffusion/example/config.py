from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent

# =========================================================
# MODEL PATHS
# =========================================================
# SD 1.5 / normal checkpoint: txt2img + img2img
MODEL_PATH = Path(
    os.getenv(
        "MODEL_PATH",
        r"F:\model\diffusion\v1-5-pruned-emaonly.safetensors",
    )
)

# Optional dedicated SD 1.5 inpainting checkpoint.
# Leave empty if you do not need / do not yet have inpainting.
INPAINT_MODEL_PATH_RAW = os.getenv("INPAINT_MODEL_PATH", "").strip()
INPAINT_MODEL_PATH = (
    Path(INPAINT_MODEL_PATH_RAW)
    if INPAINT_MODEL_PATH_RAW
    else None
)

# =========================================================
# DIRECTORIES
# =========================================================
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))
LORA_DIR = Path(os.getenv("LORA_DIR", str(BASE_DIR / "loras")))

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LORA_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# SERVER
# =========================================================
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8001"))

# =========================================================
# HARDWARE / GENERATION LIMITS
# =========================================================
DEFAULT_WIDTH = int(os.getenv("DEFAULT_WIDTH", "512"))
DEFAULT_HEIGHT = int(os.getenv("DEFAULT_HEIGHT", "512"))
MAX_WIDTH = int(os.getenv("MAX_WIDTH", "768"))
MAX_HEIGHT = int(os.getenv("MAX_HEIGHT", "768"))
DEFAULT_STEPS = int(os.getenv("DEFAULT_STEPS", "20"))
MAX_STEPS = int(os.getenv("MAX_STEPS", "40"))
DEFAULT_GUIDANCE = float(os.getenv("DEFAULT_GUIDANCE", "7.0"))
DEFAULT_STRENGTH = float(os.getenv("DEFAULT_STRENGTH", "0.55"))
MAX_BATCH = int(os.getenv("MAX_BATCH", "4"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "12"))

# 4 GB-class NVIDIA GPU + 8 GB system RAM:
# keep one diffusion request at a time.

# =========================================================
# MEMORY OPTIONS
# =========================================================
# sequential_offload = lowest VRAM usage, but slowest
# model_offload     = more VRAM, faster than sequential
OFFLOAD_MODE = os.getenv("OFFLOAD_MODE", "sequential").lower().strip()

# float16 is the normal choice for a GTX 1650-class CUDA GPU.
TORCH_DTYPE = "float16"

# =========================================================
# OPTIONAL SAFETY CHECKER
# =========================================================
# Keep enabled by default. Set to true only when you understand the tradeoff.
DISABLE_SAFETY_CHECKER = (
    os.getenv("DISABLE_SAFETY_CHECKER", "false").lower() in {"1", "true", "yes"}
)
