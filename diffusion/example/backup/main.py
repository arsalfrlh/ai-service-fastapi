from pathlib import Path
import asyncio

import torch

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backup.image_generator import ImageGenerator


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title="Local AI Image Generator",
    version="1.0.0",
)


# =========================================================
# OUTPUT
# =========================================================

OUTPUT_DIR = Path("outputs")

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


app.mount(
    "/images",
    StaticFiles(
        directory=str(OUTPUT_DIR)
    ),
    name="images",
)


# =========================================================
# LOCAL AI MODEL
# =========================================================

MODEL_PATH = r"F:\model\diffusion\v1-5-pruned-emaonly.safetensors"


# =========================================================
# IMAGE GENERATOR
# =========================================================

image_generator = ImageGenerator(
    model_path=MODEL_PATH,
    output_dir="outputs",
)


# =========================================================
# GENERATION LOCK
# =========================================================

# GTX 1650 4GB:
# satu generation pada satu waktu.

generation_lock = asyncio.Lock()


# =========================================================
# REQUEST
# =========================================================

class GenerateImageRequest(BaseModel):

    prompt: str = Field(
        min_length=1,
        max_length=2000,
    )

    negative_prompt: str = Field(
        default="",
        max_length=2000,
    )

    width: int = Field(
        default=512,
        ge=256,
        le=768,
    )

    height: int = Field(
        default=512,
        ge=256,
        le=768,
    )

    steps: int = Field(
        default=20,
        ge=1,
        le=50,
    )

    guidance_scale: float = Field(
        default=7.0,
        ge=1.0,
        le=20.0,
    )

    seed: int | None = None


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "success": True,
        "cuda": torch.cuda.is_available(),
        "gpu": (
            torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else None
        ),
        "model": MODEL_PATH,
    }


# =========================================================
# GENERATE
# =========================================================

@app.post("/generate")
async def generate_image(
    request: GenerateImageRequest
):

    if request.width % 8 != 0:
        raise HTTPException(
            status_code=400,
            detail="Width harus kelipatan 8.",
        )

    if request.height % 8 != 0:
        raise HTTPException(
            status_code=400,
            detail="Height harus kelipatan 8.",
        )

    async with generation_lock:

        try:

            result = await run_in_threadpool(
                image_generator.generate,

                prompt=request.prompt,

                negative_prompt=(
                    request.negative_prompt
                ),

                width=request.width,
                height=request.height,

                steps=request.steps,

                guidance_scale=(
                    request.guidance_scale
                ),

                seed=request.seed,
            )

            return result

        except torch.cuda.OutOfMemoryError:

            torch.cuda.empty_cache()

            raise HTTPException(
                status_code=500,
                detail=(
                    "GPU kehabisan VRAM. "
                    "Coba gunakan 512x512 "
                    "dan steps lebih rendah."
                ),
            )

        except Exception as e:

            raise HTTPException(
                status_code=500,
                detail=str(e),
            )