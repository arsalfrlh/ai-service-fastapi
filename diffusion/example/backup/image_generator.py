from pathlib import Path
from typing import Optional
import uuid

import torch
from diffusers import StableDiffusionPipeline


class ImageGenerator:

    def __init__(
        self,
        model_path: str,
        output_dir: str = "outputs",
    ):
        self.model_path = model_path

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # =================================================
        # GPU
        # =================================================

        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA tidak tersedia."
            )

        print(
            "GPU:",
            torch.cuda.get_device_name(0)
        )

        # =================================================
        # MODEL
        # =================================================

        if not Path(self.model_path).exists():
            raise FileNotFoundError(
                f"Model tidak ditemukan: {self.model_path}"
            )

        print("Model:", self.model_path)
        print("Loading Stable Diffusion...")

        self.pipe = StableDiffusionPipeline.from_single_file(
            self.model_path,
            torch_dtype=torch.float32,
        )

        # =================================================
        # VAE FIX
        # =================================================

        # Hindari numerical overflow saat VAE decode
        self.pipe.vae.config.force_upcast = True

        # =================================================
        # LOW VRAM
        # =================================================

        self.pipe.enable_sequential_cpu_offload()

        print("Stable Diffusion berhasil dimuat.")

        print("UNet dtype:", next(self.pipe.unet.parameters()).dtype)
        print("VAE dtype:", next(self.pipe.vae.parameters()).dtype)
        print(
            "Text encoder dtype:",
            next(self.pipe.text_encoder.parameters()).dtype
        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        guidance_scale: float = 7.0,
        seed: Optional[int] = None,
    ):

        if seed is None:
            seed = torch.randint(
                0,
                2**32 - 1,
                (1,),
            ).item()

        generator = torch.Generator(
            device="cuda"
        ).manual_seed(seed)

        print("=" * 60)
        print("IMAGE GENERATION")
        print("Prompt :", prompt)
        print("Size   :", f"{width}x{height}")
        print("Steps  :", steps)
        print("Seed   :", seed)
        print("=" * 60)

        with torch.inference_mode():

            result = self.pipe(
                prompt=prompt,

                negative_prompt=negative_prompt,

                width=width,
                height=height,

                num_inference_steps=steps,

                guidance_scale=guidance_scale,

                generator=generator,

                output_type="pil",
            )

        image = result.images[0]

        filename = f"{uuid.uuid4().hex}.png"

        output_path = (
            self.output_dir / filename
        )

        image.save(output_path)

        print("Generation selesai.")
        print("Output:", output_path)

        return {
            "success": True,
            "image_id": uuid.uuid4().hex,
            "filename": filename,
            "path": str(output_path),

            "prompt": prompt,
            "negative_prompt": negative_prompt,

            "width": width,
            "height": height,

            "steps": steps,
            "guidance_scale": guidance_scale,

            "seed": seed,

            "model": self.model_path,
        }