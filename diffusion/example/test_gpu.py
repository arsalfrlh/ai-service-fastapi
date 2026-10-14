import torch

print("=" * 60)
print("LOCAL AI GPU CHECK")
print("=" * 60)
print("PyTorch:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
print("CUDA runtime:", torch.version.cuda)

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    props = torch.cuda.get_device_properties(0)
    print(f"VRAM: {props.total_memory / 1024**3:.2f} GB")

    x = torch.randn((2, 3, 512, 512), device="cuda", dtype=torch.float16)
    y = x * 2
    torch.cuda.synchronize()
    print("CUDA tensor test: OK")
    print("Tensor device:", y.device)
    del x, y
    torch.cuda.empty_cache()
else:
    print("GPU tidak terdeteksi oleh PyTorch.")
    print("Jalankan: nvidia-smi")
    print("Jika nvidia-smi bekerja tetapi CUDA=False, biasanya PyTorch yang terpasang adalah +cpu.")

print("=" * 60)
