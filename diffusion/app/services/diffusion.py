import os
import threading
import time
import torch
from diffusers import StableDiffusionPipeline, AutoPipelineForImage2Image, AutoPipelineForInpainting
from app.core.config import MODEL_PATH
from PIL import Image

class DiffusionService:
    def __init__(self):
        self.pipe: StableDiffusionPipeline | None = None
        self.image2image_pipe: AutoPipelineForImage2Image | None = None
        self.inpaint_pipe: AutoPipelineForInpainting | None = None
        self.lock = threading.Lock() # Untuk sementara generation dibuat satu per satu. Ini penting karena satu pipeline tidak perlu menerima banyak proses generation secara bersamaan pada laptop CPU.

    def load_model(self):
        if self.pipe is not None:
            return

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model tidak ditemukan: {MODEL_PATH}")

        print("=" * 60)
        print("LOADING STABLE DIFFUSION")
        print("=" * 60)
        print(f"Model : {MODEL_PATH}")
        print("Device: CPU")

        start_time = time.time()
        self.pipe = StableDiffusionPipeline.from_single_file( #load single model
            MODEL_PATH,
            torch_dtype=torch.float32 #menggunakan float32
        )
        self.pipe = self.pipe.to("cpu") #pipe di proses di cpu
        self.pipe.set_progress_bar_config(disable=False)
        elapsed = time.time() - start_time
        print(f"Model berhasil dimuat dalam {elapsed:.2f} detik")
        print("=" * 60)

    def load_image2image_pipeline(self):
        if self.pipe is None:
            self.load_model()

        if self.image2image_pipe is not None:
            return

        print("=" * 60)
        print("CREATING IMAGE TO IMAGE PIPELINE")
        print("=" * 60)
        start_time = time.time()
        self.image2image_pipe = AutoPipelineForImage2Image.from_pipe(
            self.pipe
        )
        self.image2image_pipe.set_progress_bar_config(disable=False)
        elapsed = time.time() - start_time
        print(f"Model berhasil dimuat dalam {elapsed:.2f} detik")
        print("=" * 60)

    def load_inpaint_pipeline(self):
        if self.pipe is None:
            self.load_model()
            
        if self.inpaint_pipe is not None:
            return

        print("=" * 60)
        print("CREATING INPAINTING PIPELINE")
        print("=" * 60)
        start_time = time.time()
        self.inpaint_pipe = AutoPipelineForInpainting.from_pipe(
            self.pipe
        )
        self.inpaint_pipe.set_progress_bar_config(disable=False)
        elapsed = time.time() - start_time
        print(f"Model berhasil dimuat dalam {elapsed:.2f} detik")
        print("=" * 60)

    def generate_text_to_image(
        self,
        prompt: str,
        negative_prompt: str | None = None,
        width: int = 512,
        height: int = 512,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        seed: int | None = None,
    ):
        if self.pipe is None:
            self.load_model()
        if seed is None:
            seed = torch.randint(0,2**32 - 1, (1,)).item()
        generator = torch.Generator(device="cpu").manual_seed(seed)

        print()
        print("=" * 60)
        print("TEXT TO IMAGE")
        print("=" * 60)
        print(f"Prompt      : {prompt}")
        print(f"Negative    : {negative_prompt}")
        print(f"Resolution  : {width}x{height}")
        print(f"Steps       : {num_inference_steps}")
        print(f"Guidance    : {guidance_scale}")
        print(f"Seed        : {seed}")

        start_time = time.time()
        with self.lock:
            result = self.pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )

        image = result.images[0]
        elapsed = time.time() - start_time
        print(f"Generation selesai: {elapsed:.2f} detik")
        print("=" * 60)
        return image, seed #return data tuple| contoh penggunaan: image_result, seed_result = generate_text_to_image(...)

    def generate_image_to_image(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str | None = None,
        strength: float = 0.75,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        seed: int | None = None,
        width: int = 512,
        height: int = 512,
    ):
        self.load_image2image_pipeline()
        if seed is None:
            seed = torch.randint(0,2**32 - 1,(1,),).item()
        generator = torch.Generator(device="cpu").manual_seed(seed)
        image = image.convert("RGB")
        image = image.resize((width, height)) #sementara di resize

        print()
        print("=" * 60)
        print("IMAGE TO IMAGE")
        print("=" * 60)
        print(f"Prompt      : {prompt}")
        print(f"Negative    : {negative_prompt}")
        print(f"Strength    : {strength}")
        print(f"Resolution  : {width}x{height}")
        print(f"Steps       : {num_inference_steps}")
        print(f"Guidance    : {guidance_scale}")
        print(f"Seed        : {seed}")

        start_time = time.time()
        with self.lock:
            result = self.image2image_pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )

        output_image = result.images[0]
        elapsed = time.time() - start_time
        print(f"Generation selesai: {elapsed:.2f} detik")
        print("=" * 60)
        return output_image, seed

    def generate_inpainting_image(
        self,
        image: Image.Image,
        mask_image: Image.Image,
        prompt: str,
        negative_prompt: str = None,
        strength: float = 0.8,
        num_inference_steps: int = 20,
        guidance_scale: float = 7.5,
        seed: int = None,
        width: int = 512,
        height: int = 512,
    ):
        self.load_inpaint_pipeline()
        if seed is None:
            seed = torch.randint(0,2**32 - 1,(1,),).item()
        generator = torch.Generator(device="cpu").manual_seed(seed)
        image = image.convert("RGB")
        image = image.resize((width, height))
        mask_image = mask_image.convert("L")
        mask_image = mask_image.resize((width, height),Image.Resampling.NEAREST,)

        print()
        print("=" * 60)
        print("INPAINTING")
        print("=" * 60)
        print(f"Prompt      : {prompt}")
        print(f"Negative    : {negative_prompt}")
        print(f"Strength    : {strength}")
        print(f"Resolution  : {width}x{height}")
        print(f"Steps       : {num_inference_steps}")
        print(f"Guidance    : {guidance_scale}")
        print(f"Seed        : {seed}")
        start_time = time.time()

        with self.lock:
            result = self.inpaint_pipe(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=image,
                mask_image=mask_image,
                strength=strength,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale,
                generator=generator
            )

        output_image = result.images[0]
        elapsed = time.time() - start_time
        print(f"Generation selesai: {elapsed:.2f} detik")
        return output_image, seed

diffusion_service = DiffusionService()