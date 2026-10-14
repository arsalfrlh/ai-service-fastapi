# Local AI Image Generator - Stable Diffusion 1.5

Local FastAPI service for a low-VRAM NVIDIA GPU.

## Supported features

- text-to-image
- image-to-image
- true inpainting with a dedicated SD 1.5 inpainting checkpoint
- negative prompt
- seed / reproducible generation
- sequential multi-image generation
- Euler / Euler Ancestral / DDIM / DPM++ 2M Karras schedulers
- per-request local LoRA
- PNG metadata + JSON sidecar
- VAE slicing + tiling
- sequential CPU offload
- health, model info, GPU memory info

## Hardware target

Recommended baseline for this version:

- Ryzen 5 5500-class CPU
- 8 GB system RAM
- GTX 1650-class NVIDIA GPU with around 4 GB VRAM
- Stable Diffusion 1.5 checkpoint

Use 512x512, 15-25 steps, one image at a time for the safest memory usage.

## 1. Create venv

```powershell
cd E:\Project\ai
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -U pip
```

## 2. Install CUDA PyTorch

Remove CPU-only PyTorch first:

```powershell
pip uninstall torch torchvision torchaudio -y
```

Then install the CUDA build matching the current PyTorch wheel index:

```powershell
pip install torch==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
```

Then install the service dependencies:

```powershell
pip install -r requirements.txt
```

## 3. Check the GPU

```powershell
nvidia-smi
python test_gpu.py
```

You need:

```text
CUDA available: True
GPU: NVIDIA GeForce GTX 1650
```

## 4. Put your model in the config path

Default example:

```text
F:\model\diffusion\v1-5-pruned-emaonly.safetensors
```

You can also set MODEL_PATH as an environment variable.

## 5. Optional inpainting model

A normal SD 1.5 checkpoint is not a true inpainting checkpoint. Put a dedicated SD 1.5 inpainting checkpoint somewhere and set:

```powershell
$env:INPAINT_MODEL_PATH="F:\model\diffusion\sd-v1-5-inpainting.safetensors"
```

The service loads this model only for an /inpaint request and then releases it before restoring the base model. This intentionally trades speed for lower system RAM pressure.

## 6. Optional LoRA

Put LoRA files here:

```text
loras/
  anime.safetensors
  photorealistic.safetensors
```

Then send `lora_name=anime.safetensors` and `lora_scale=0.8`.

## 7. Start the API

```powershell
python app.py
```

or:

```powershell
uvicorn app:app --host 127.0.0.1 --port 8001 --workers 1
```

Open:

```text
http://127.0.0.1:8001/docs
```

Do NOT run multiple workers because each worker would initialize another copy of the diffusion model.

## API examples

### Text-to-image

```powershell
curl.exe -X POST "http://127.0.0.1:8001/generate" `
  -F "prompt=a cinematic portrait of a young man in a rainy cyberpunk city, detailed face, dramatic lighting" `
  -F "negative_prompt=blurry, low quality, deformed, bad anatomy" `
  -F "width=512" `
  -F "height=512" `
  -F "steps=20" `
  -F "guidance_scale=7" `
  -F "seed=12345" `
  -F "scheduler=euler_a"
```

### Image-to-image

```powershell
curl.exe -X POST "http://127.0.0.1:8001/img2img" `
  -F "image=@input.png" `
  -F "prompt=turn this sketch into a detailed fantasy illustration" `
  -F "negative_prompt=blurry, low quality" `
  -F "strength=0.55" `
  -F "steps=20" `
  -F "guidance_scale=7" `
  -F "seed=12345" `
  -F "scheduler=euler_a"
```

### Inpaint

White mask = area to repaint, black mask = area to preserve.

```powershell
curl.exe -X POST "http://127.0.0.1:8001/inpaint" `
  -F "image=@input.png" `
  -F "mask=@mask.png" `
  -F "prompt=replace the masked object with a modern black smartphone" `
  -F "negative_prompt=blurry, distorted, low quality" `
  -F "strength=0.85" `
  -F "mask_blur=4" `
  -F "steps=20" `
  -F "guidance_scale=7" `
  -F "seed=12345"
```

## Output

Every generation creates:

```text
outputs/<uuid>.png
outputs/<uuid>.json
```

The PNG also stores generation metadata such as prompt, negative prompt, seed and scheduler.

## Important GTX 1650 settings

Use first:

```text
512x512
20 steps
Euler Ancestral
CFG 6.5-8
strength 0.45-0.70 for img2img
1 image/request
```

For stronger GPU memory savings:

```text
OFFLOAD_MODE=sequential
```

For somewhat better speed at the cost of more VRAM:

```text
OFFLOAD_MODE=model
```

Do not expect modern multi-billion-parameter image models to behave like SD 1.5 on this hardware.
