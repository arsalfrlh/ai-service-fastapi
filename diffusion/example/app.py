from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from typing import Optional

import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from config import (
    HOST,
    MAX_UPLOAD_MB,
    OUTPUT_DIR,
    PORT,
)
from image_generator import ImageGenerator


app = FastAPI(
    title="Local AI Image Generator",
    version="2.0.0",
    description=(
        "Local Stable Diffusion API optimized for low-VRAM NVIDIA GPUs. "
        "Supports text-to-image, image-to-image and optional inpainting."
    ),
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/images",
    StaticFiles(directory=str(OUTPUT_DIR)),
    name="images",
)


# DO NOT use uvicorn --workers > 1 for this service.
# Every worker would create another copy of the model.
generator = ImageGenerator()
generation_lock = asyncio.Lock()


# =========================================================
# HELPERS
# =========================================================

async def read_image_upload(upload: UploadFile, *, required: bool = True) -> Optional[Image.Image]:
    if upload is None:
        if required:
            raise HTTPException(status_code=400, detail="File gambar wajib diisi.")
        return None

    content = await upload.read()
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran file terlalu besar. Maksimum {MAX_UPLOAD_MB} MB.",
        )

    try:
        image = Image.open(BytesIO(content))
        image.load()
        return image.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="File bukan gambar yang valid.",
        ) from exc


async def read_mask_upload(upload: UploadFile) -> Image.Image:
    content = await upload.read()
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Ukuran mask terlalu besar. Maksimum {MAX_UPLOAD_MB} MB.",
        )

    try:
        image = Image.open(BytesIO(content))
        image.load()
        return image.convert("L")
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Mask bukan gambar yang valid.",
        ) from exc


def handle_generation_error(exc: Exception) -> HTTPException:
    if isinstance(exc, torch.cuda.OutOfMemoryError):
        torch.cuda.empty_cache()
        return HTTPException(
            status_code=507,
            detail=(
                "GPU kehabisan VRAM. Gunakan 512x512, steps 15-25, "
                "num_images=1, dan hindari beberapa model/LoRA sekaligus."
            ),
        )

    if isinstance(exc, (ValueError, FileNotFoundError, RuntimeError)):
        return HTTPException(status_code=400, detail=str(exc))

    return HTTPException(status_code=500, detail=str(exc))


# =========================================================
# ROOT / HEALTH
# =========================================================

@app.get("/")
async def root():
    return {
        "service": "Local AI Image Generator",
        "version": app.version,
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "text_to_image": "POST /generate",
            "image_to_image": "POST /img2img",
            "inpaint": "POST /inpaint",
            "loras": "GET /loras",
        },
    }


@app.get("/health")
async def health():
    cuda = torch.cuda.is_available()
    return {
        "success": True,
        "cuda": cuda,
        "gpu": torch.cuda.get_device_name(0) if cuda else None,
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda if cuda else None,
        "model": str(generator.model_path),
        "model_exists": generator.model_path.exists(),
    }


@app.get("/info")
async def info():
    return generator.info()


@app.get("/loras")
async def loras():
    return {
        "success": True,
        "items": generator.list_loras(),
    }


# =========================================================
# TEXT -> IMAGE
# =========================================================

@app.post("/generate")
async def generate_image(
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: int = Form(512),
    height: int = Form(512),
    steps: int = Form(20),
    guidance_scale: float = Form(7.0),
    seed: Optional[int] = Form(None),
    scheduler: str = Form("euler_a"),
    num_images: int = Form(1),
    lora_name: Optional[str] = Form(None),
    lora_scale: float = Form(0.8),
):
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt wajib diisi.")

    if not 1 <= num_images <= 4:
        raise HTTPException(status_code=400, detail="num_images harus 1-4.")

    async with generation_lock:
        try:
            return await run_in_threadpool(
                generator.generate_text_to_image,
                prompt,
                negative_prompt,
                width,
                height,
                steps,
                guidance_scale,
                seed,
                scheduler,
                num_images,
                lora_name,
                lora_scale,
            )
        except Exception as exc:
            raise handle_generation_error(exc)


# =========================================================
# IMAGE + PROMPT -> IMAGE
# =========================================================

@app.post("/img2img")
async def image_to_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    steps: int = Form(20),
    guidance_scale: float = Form(7.0),
    strength: float = Form(0.55),
    seed: Optional[int] = Form(None),
    scheduler: str = Form("euler_a"),
    num_images: int = Form(1),
    resize_mode: str = Form("fit"),
    lora_name: Optional[str] = Form(None),
    lora_scale: float = Form(0.8),
):
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt wajib diisi.")

    source = await read_image_upload(image)

    if not 1 <= num_images <= 4:
        raise HTTPException(status_code=400, detail="num_images harus 1-4.")

    async with generation_lock:
        try:
            return await run_in_threadpool(
                generator.generate_image_to_image,
                source,
                prompt,
                negative_prompt,
                width,
                height,
                steps,
                guidance_scale,
                strength,
                seed,
                scheduler,
                num_images,
                resize_mode,
                lora_name,
                lora_scale,
                image.filename,
            )
        except Exception as exc:
            raise handle_generation_error(exc)


# =========================================================
# IMAGE + MASK + PROMPT -> INPAINT
# =========================================================

@app.post("/inpaint")
async def inpaint(
    image: UploadFile = File(...),
    mask: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str = Form(""),
    width: Optional[int] = Form(None),
    height: Optional[int] = Form(None),
    steps: int = Form(20),
    guidance_scale: float = Form(7.0),
    strength: float = Form(0.85),
    seed: Optional[int] = Form(None),
    scheduler: str = Form("euler_a"),
    num_images: int = Form(1),
    mask_blur: int = Form(4),
    lora_name: Optional[str] = Form(None),
    lora_scale: float = Form(0.8),
):
    prompt = prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt wajib diisi.")

    source = await read_image_upload(image)
    mask_image = await read_mask_upload(mask)

    if not 1 <= num_images <= 4:
        raise HTTPException(status_code=400, detail="num_images harus 1-4.")

    async with generation_lock:
        try:
            return await run_in_threadpool(
                generator.generate_inpaint,
                source,
                mask_image,
                prompt,
                negative_prompt,
                width,
                height,
                steps,
                guidance_scale,
                strength,
                seed,
                scheduler,
                num_images,
                mask_blur,
                lora_name,
                lora_scale,
                image.filename,
            )
        except Exception as exc:
            raise handle_generation_error(exc)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=False,
        workers=1,
    )
