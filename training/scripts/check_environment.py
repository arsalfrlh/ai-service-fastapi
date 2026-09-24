import sys
import torch
import transformers
import datasets
import peft
import trl
import accelerate
import bitsandbytes

print("=" * 60)
print("QWEN FINE-TUNING ENVIRONMENT")
print("=" * 60)

print(f"Python        : {sys.version}")
print(f"PyTorch       : {torch.__version__}")
print(f"Transformers  : {transformers.__version__}")
print(f"Datasets      : {datasets.__version__}")
print(f"PEFT          : {peft.__version__}")
print(f"TRL           : {trl.__version__}")
print(f"Accelerate    : {accelerate.__version__}")
print(f"BitsAndBytes  : {bitsandbytes.__version__}")

print("-" * 60)

print(f"CUDA available : {torch.cuda.is_available()}")
print(f"CUDA version   : {torch.version.cuda}")

if torch.cuda.is_available():
    gpu = torch.cuda.get_device_properties(0)

    print(f"GPU            : {gpu.name}")
    print(f"VRAM           : {gpu.total_memory / 1024**3:.2f} GB")
    print(f"Compute Cap.   : {gpu.major}.{gpu.minor}")

print("=" * 60)