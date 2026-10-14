from __future__ import annotations

import gc
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

import torch
from PIL import Image, ImageFilter, ImageOps, PngImagePlugin

from diffusers import (
    DDIMScheduler,
    DPMSolverMultistepScheduler,
    EulerAncestralDiscreteScheduler,
    EulerDiscreteScheduler,
    StableDiffusionInpaintPipeline,
    StableDiffusionPipeline,
)

from config import (
    DEFAULT_GUIDANCE,
    DEFAULT_HEIGHT,
    DEFAULT_STEPS,
    DEFAULT_STRENGTH,
    DEFAULT_WIDTH,
    DISABLE_SAFETY_CHECKER,
    INPAINT_MODEL_PATH,
    LORA_DIR,
    MAX_BATCH,
    MAX_HEIGHT,
    MAX_STEPS,
    MAX_WIDTH,
    MODEL_PATH,
    OFFLOAD_MODE,
    OUTPUT_DIR,
)


class ImageGenerator:
    """
    Local Stable Diffusion 1.5 engine optimized for low VRAM.

    Features:
      - text-to-image
      - image-to-image
      - inpainting with a dedicated inpainting checkpoint
      - negative prompt
      - seed / reproducibility
      - multiple images per request (generated sequentially)
      - scheduler selection
      - per-request LoRA loading
      - PNG metadata + JSON metadata sidecar
      - VAE slicing/tiling
      - CUDA memory reporting
    """

    SUPPORTED_SCHEDULERS = {
        "euler": "EulerDiscreteScheduler",
        "euler_a": "EulerAncestralDiscreteScheduler",
        "ddim": "DDIMScheduler",
        "dpmpp_2m": "DPMSolverMultistepScheduler (DPM++ 2M Karras)",
    }

    def __init__(
        self,
        model_path: str | Path = MODEL_PATH,
        output_dir: str | Path = OUTPUT_DIR,
    ) -> None:
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.inpaint_model_path = INPAINT_MODEL_PATH
        self._inpaint_pipe: Optional[StableDiffusionInpaintPipeline] = None
        self._img2img_pipe = None
        self._loaded_lora: Optional[str] = None

        self._check_cuda()
        self._load_base_pipeline()
        self._prepare_directories()

    # =========================================================
    # HARDWARE
    # =========================================================

    @staticmethod
    def _check_cuda() -> None:
        if not torch.cuda.is_available():
            raise RuntimeError(
                "CUDA tidak tersedia. Pastikan PyTorch yang terpasang adalah "
                "build CUDA, bukan versi +cpu. Jalankan nvidia-smi dan test_gpu.py."
            )

        print("=" * 70)
        print("CUDA DEVICE")
        print("=" * 70)
        print("GPU:", torch.cuda.get_device_name(0))
        props = torch.cuda.get_device_properties(0)
        print(f"VRAM: {props.total_memory / 1024**3:.2f} GB")
        print("CUDA runtime:", torch.version.cuda)
        print("PyTorch:", torch.__version__)
        print("=" * 70)

    @staticmethod
    def _cuda_memory() -> dict:
        if not torch.cuda.is_available():
            return {
                "available": False,
                "total_gb": 0,
                "free_gb": 0,
                "used_gb": 0,
            }

        free_bytes, total_bytes = torch.cuda.mem_get_info()
        return {
            "available": True,
            "total_gb": round(total_bytes / 1024**3, 2),
            "free_gb": round(free_bytes / 1024**3, 2),
            "used_gb": round((total_bytes - free_bytes) / 1024**3, 2),
        }

    # =========================================================
    # MODEL
    # =========================================================

    def _prepare_directories(self) -> None:
        LORA_DIR.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_base_pipeline(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Base model tidak ditemukan: {self.model_path}"
            )

        print("Loading base model:", self.model_path)
        print("dtype: float32")
        print("offload:", OFFLOAD_MODE)

        kwargs = {
            "torch_dtype": torch.float32,
        }

        # Disabling the safety checker is optional. By default it remains enabled.
        if DISABLE_SAFETY_CHECKER:
            kwargs["safety_checker"] = None
            kwargs["requires_safety_checker"] = False

        self.pipe = StableDiffusionPipeline.from_single_file(
            str(self.model_path),
            **kwargs,
        )

        self._configure_pipeline(self.pipe)

        # IMPORTANT:
        # from_pipe() reuses the already loaded component objects, so we don't
        # load the SD model a second time just to support img2img.
        from diffusers import AutoPipelineForImage2Image

        self._img2img_pipe = AutoPipelineForImage2Image.from_pipe(self.pipe)

        print("Base model loaded.")
        print("UNet input channels:", self.pipe.unet.config.in_channels)
        print("VAE force_upcast:", getattr(self.pipe.vae.config, "force_upcast", None))
        print("VRAM after load:", self._cuda_memory())

    def _configure_pipeline(self, pipe) -> None:
        # Numerical stability for VAE decode on older consumer GPUs/checkpoints.
        if getattr(pipe, "vae", None) is not None:
            pipe.vae.config.force_upcast = True
            if hasattr(pipe.vae, "enable_slicing"):
                pipe.vae.enable_slicing()

        # Tiling helps when using larger output sizes.
        if hasattr(pipe, "enable_vae_tiling"):
            pipe.enable_vae_tiling()

        # Diffusers recommends native SDPA when using modern PyTorch rather than
        # forcing attention slicing. Attention slicing can conflict with SDPA.
        # See the official memory docs linked in the explanation.

        if OFFLOAD_MODE == "model":
            pipe.enable_model_cpu_offload()
        else:
            pipe.enable_sequential_cpu_offload()

        pipe.set_progress_bar_config(disable=False)

    def _load_inpaint_pipeline(self) -> StableDiffusionInpaintPipeline:
        if self.inpaint_model_path is None:
            raise RuntimeError(
                "INPAINT_MODEL_PATH belum diisi. True inpainting membutuhkan "
                "checkpoint Stable Diffusion inpainting (UNet 9-channel), "
                "bukan checkpoint SD 1.5 biasa."
            )

        if not self.inpaint_model_path.exists():
            raise FileNotFoundError(
                f"Inpaint model tidak ditemukan: {self.inpaint_model_path}"
            )

        if self._inpaint_pipe is not None:
            return self._inpaint_pipe

        print("Loading inpaint model:", self.inpaint_model_path)

        # Avoid keeping another full pipeline in RAM at the same time as the base
        # pipeline. The model is lazily loaded only when /inpaint is used.
        self._release_base_pipeline()

        kwargs = {"torch_dtype": torch.float32}
        if DISABLE_SAFETY_CHECKER:
            kwargs["safety_checker"] = None
            kwargs["requires_safety_checker"] = False

        try:
            self._inpaint_pipe = StableDiffusionInpaintPipeline.from_single_file(
                str(self.inpaint_model_path),
                **kwargs,
            )
            self._configure_pipeline(self._inpaint_pipe)

            in_channels = self._inpaint_pipe.unet.config.in_channels
            if in_channels != 9:
                raise RuntimeError(
                    f"Checkpoint inpaint memiliki UNet in_channels={in_channels}. "
                    "Untuk SD 1.5 inpainting yang umum, gunakan checkpoint dengan "
                    "UNet 9-channel."
                )

            print("Inpaint model loaded.")
            return self._inpaint_pipe
        except Exception:
            # Loading inpaint temporarily replaces the base pipeline. If anything
            # fails, restore the base pipeline so the API remains usable.
            self._release_inpaint_pipeline()
            self._restore_base_pipeline()
            raise

    def _release_inpaint_pipeline(self) -> None:
        if self._inpaint_pipe is not None:
            try:
                self._inpaint_pipe.to("cpu")
            except Exception:
                pass
            del self._inpaint_pipe
            self._inpaint_pipe = None

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def _release_base_pipeline(self) -> None:
        # The component modules referenced by _img2img_pipe are shared with pipe.
        self._img2img_pipe = None

        if hasattr(self, "pipe") and self.pipe is not None:
            try:
                self.pipe.to("cpu")
            except Exception:
                pass
            del self.pipe

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

    def _restore_base_pipeline(self) -> None:
        if hasattr(self, "pipe") and self.pipe is not None:
            return
        self._load_base_pipeline()

    # =========================================================
    # VALIDATION / IMAGE HELPERS
    # =========================================================

    @staticmethod
    def validate_dimensions(width: int, height: int) -> None:
        if width < 256 or height < 256:
            raise ValueError("Ukuran minimum adalah 256x256.")
        if width > MAX_WIDTH or height > MAX_HEIGHT:
            raise ValueError(
                f"Ukuran maksimum adalah {MAX_WIDTH}x{MAX_HEIGHT}."
            )
        if width % 8 != 0 or height % 8 != 0:
            raise ValueError("Width dan height harus kelipatan 8.")

    @staticmethod
    def _round_down_8(value: int) -> int:
        return max(256, value - (value % 8))

    def resolve_img2img_size(
        self,
        image: Image.Image,
        width: Optional[int],
        height: Optional[int],
    ) -> tuple[int, int]:
        source_w, source_h = image.size

        width = width or self._round_down_8(min(source_w, DEFAULT_WIDTH))
        height = height or self._round_down_8(min(source_h, DEFAULT_HEIGHT))

        self.validate_dimensions(width, height)
        return width, height

    @staticmethod
    def resize_image(
        image: Image.Image,
        width: int,
        height: int,
        mode: str = "fit",
    ) -> Image.Image:
        image = image.convert("RGB")
        mode = mode.lower()

        if mode == "stretch":
            return image.resize((width, height), Image.Resampling.LANCZOS)

        # fit = preserve aspect ratio and crop the excess area.
        return ImageOps.fit(
            image,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )

    @staticmethod
    def prepare_mask(
        mask: Image.Image,
        size: tuple[int, int],
        blur: int = 0,
    ) -> Image.Image:
        mask = mask.convert("L").resize(size, Image.Resampling.LANCZOS)
        if blur > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=blur))
        return mask

    @staticmethod
    def _new_seed(seed: Optional[int]) -> int:
        if seed is not None:
            return int(seed) % (2**32)
        return int(torch.randint(0, 2**32 - 1, (1,), device="cpu").item())

    @staticmethod
    def _generator(seed: int) -> torch.Generator:
        return torch.Generator(device="cuda").manual_seed(seed)

    # =========================================================
    # SCHEDULER
    # =========================================================

    def set_scheduler(self, pipe, name: str) -> None:
        name = name.lower().strip()
        if name not in self.SUPPORTED_SCHEDULERS:
            raise ValueError(
                f"Scheduler tidak didukung: {name}. "
                f"Pilih: {', '.join(self.SUPPORTED_SCHEDULERS.keys())}"
            )

        config = pipe.scheduler.config

        if name == "euler":
            pipe.scheduler = EulerDiscreteScheduler.from_config(config)
            return

        if name == "euler_a":
            pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(config)
            return

        if name == "ddim":
            pipe.scheduler = DDIMScheduler.from_config(config)
            return

        if name == "dpmpp_2m":
            scheduler = DPMSolverMultistepScheduler.from_config(config)
            if hasattr(scheduler, "algorithm_type"):
                scheduler.algorithm_type = "dpmsolver++"
            if hasattr(scheduler, "use_karras_sigmas"):
                scheduler.use_karras_sigmas = True
            pipe.scheduler = scheduler

    # =========================================================
    # LORA
    # =========================================================

    def _resolve_lora(self, lora_name: Optional[str]) -> Optional[Path]:
        if not lora_name:
            return None

        # Security: only allow a filename inside LORA_DIR; never accept an
        # arbitrary user supplied filesystem path from HTTP.
        candidate = Path(lora_name).name
        path = (LORA_DIR / candidate).resolve()
        lora_root = LORA_DIR.resolve()

        if lora_root not in path.parents:
            raise ValueError("Path LoRA tidak valid.")

        if path.suffix.lower() not in {".safetensors", ".pt", ".bin"}:
            raise ValueError("Format LoRA harus .safetensors, .pt, atau .bin.")

        if not path.exists():
            raise FileNotFoundError(f"LoRA tidak ditemukan: {candidate}")

        return path

    @contextmanager
    def _lora_context(
        self,
        pipe,
        lora_name: Optional[str],
        lora_scale: float,
    ) -> Iterator[None]:
        lora_path = self._resolve_lora(lora_name)
        if lora_path is None:
            yield
            return

        adapter = "request_lora"
        print(f"Loading LoRA: {lora_path.name} scale={lora_scale}")

        try:
            pipe.load_lora_weights(
                str(lora_path),
                adapter_name=adapter,
                low_cpu_mem_usage=True,
            )
            pipe.set_adapters(
                adapter,
                adapter_weights=float(lora_scale),
            )
            self._loaded_lora = lora_path.name
            yield
        finally:
            try:
                pipe.unload_lora_weights()
            except Exception:
                pass
            self._loaded_lora = None

    # =========================================================
    # SAVE
    # =========================================================

    def _save_result(
        self,
        image: Image.Image,
        *,
        mode: str,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        guidance_scale: float,
        strength: Optional[float],
        seed: int,
        scheduler: str,
        lora_name: Optional[str],
        lora_scale: float,
        source_filename: Optional[str] = None,
    ) -> dict:
        image_id = uuid.uuid4().hex
        filename = f"{image_id}.png"
        json_filename = f"{image_id}.json"

        image_path = self.output_dir / filename
        json_path = self.output_dir / json_filename

        metadata = {
            "image_id": image_id,
            "filename": filename,
            "mode": mode,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "strength": strength,
            "seed": seed,
            "scheduler": scheduler,
            "lora": lora_name,
            "lora_scale": lora_scale if lora_name else None,
            "source_filename": source_filename,
            "model": str(self.model_path),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }

        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("prompt", prompt)
        png_info.add_text("negative_prompt", negative_prompt)
        png_info.add_text("mode", mode)
        png_info.add_text("seed", str(seed))
        png_info.add_text("scheduler", scheduler)
        png_info.add_text("steps", str(steps))
        png_info.add_text("guidance_scale", str(guidance_scale))
        if strength is not None:
            png_info.add_text("strength", str(strength))
        if lora_name:
            png_info.add_text("lora", lora_name)
            png_info.add_text("lora_scale", str(lora_scale))

        image.save(image_path, pnginfo=png_info)
        json_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        return {
            "image_id": image_id,
            "filename": filename,
            "json_filename": json_filename,
            "path": str(image_path),
            "metadata_path": str(json_path),
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "mode": mode,
            "width": width,
            "height": height,
            "steps": steps,
            "guidance_scale": guidance_scale,
            "strength": strength,
            "seed": seed,
            "scheduler": scheduler,
            "lora": lora_name,
            "lora_scale": lora_scale if lora_name else None,
            "model": str(self.model_path),
        }

    # =========================================================
    # TEXT TO IMAGE
    # =========================================================

    def generate_text_to_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        steps: int = DEFAULT_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE,
        seed: Optional[int] = None,
        scheduler: str = "euler_a",
        num_images: int = 1,
        lora_name: Optional[str] = None,
        lora_scale: float = 0.8,
    ) -> dict:
        self.validate_dimensions(width, height)
        steps = max(1, min(steps, MAX_STEPS))
        num_images = max(1, min(num_images, MAX_BATCH))
        seed = self._new_seed(seed)

        self.set_scheduler(self.pipe, scheduler)

        results = []
        started = time.perf_counter()

        print("=" * 70)
        print("TEXT TO IMAGE")
        print("prompt:", prompt)
        print("size:", f"{width}x{height}")
        print("steps:", steps)
        print("guidance:", guidance_scale)
        print("seed base:", seed)
        print("scheduler:", scheduler)
        print("=" * 70)

        with self._lora_context(self.pipe, lora_name, lora_scale):
            for index in range(num_images):
                current_seed = (seed + index) % (2**32)
                generator = self._generator(current_seed)

                with torch.inference_mode():
                    output = self.pipe(
                        prompt=prompt,
                        negative_prompt=negative_prompt or None,
                        width=width,
                        height=height,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        output_type="pil",
                    )

                image = output.images[0]
                results.append(
                    self._save_result(
                        image,
                        mode="txt2img",
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        steps=steps,
                        guidance_scale=guidance_scale,
                        strength=None,
                        seed=current_seed,
                        scheduler=scheduler,
                        lora_name=lora_name,
                        lora_scale=lora_scale,
                    )
                )

                del output, image, generator
                gc.collect()
                torch.cuda.empty_cache()

        elapsed = round(time.perf_counter() - started, 3)
        return {
            "success": True,
            "count": len(results),
            "elapsed_seconds": elapsed,
            "results": results,
            "gpu_memory": self._cuda_memory(),
        }

    # =========================================================
    # IMAGE TO IMAGE
    # =========================================================

    def generate_image_to_image(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: int = DEFAULT_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE,
        strength: float = DEFAULT_STRENGTH,
        seed: Optional[int] = None,
        scheduler: str = "euler_a",
        num_images: int = 1,
        resize_mode: str = "fit",
        lora_name: Optional[str] = None,
        lora_scale: float = 0.8,
        source_filename: Optional[str] = None,
    ) -> dict:
        width, height = self.resolve_img2img_size(image, width, height)
        steps = max(1, min(steps, MAX_STEPS))
        num_images = max(1, min(num_images, MAX_BATCH))
        strength = max(0.01, min(float(strength), 0.99))
        seed = self._new_seed(seed)

        image = self.resize_image(image, width, height, resize_mode)
        self.set_scheduler(self._img2img_pipe, scheduler)

        results = []
        started = time.perf_counter()

        with self._lora_context(self._img2img_pipe, lora_name, lora_scale):
            for index in range(num_images):
                current_seed = (seed + index) % (2**32)
                generator = self._generator(current_seed)

                with torch.inference_mode():
                    output = self._img2img_pipe(
                        prompt=prompt,
                        negative_prompt=negative_prompt or None,
                        image=image,
                        strength=strength,
                        num_inference_steps=steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                        output_type="pil",
                    )

                result_image = output.images[0]
                results.append(
                    self._save_result(
                        result_image,
                        mode="img2img",
                        prompt=prompt,
                        negative_prompt=negative_prompt,
                        width=width,
                        height=height,
                        steps=steps,
                        guidance_scale=guidance_scale,
                        strength=strength,
                        seed=current_seed,
                        scheduler=scheduler,
                        lora_name=lora_name,
                        lora_scale=lora_scale,
                        source_filename=source_filename,
                    )
                )

                del output, result_image, generator
                gc.collect()
                torch.cuda.empty_cache()

        elapsed = round(time.perf_counter() - started, 3)
        return {
            "success": True,
            "count": len(results),
            "elapsed_seconds": elapsed,
            "results": results,
            "gpu_memory": self._cuda_memory(),
        }

    # =========================================================
    # INPAINT
    # =========================================================

    def generate_inpaint(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        negative_prompt: str = "",
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: int = DEFAULT_STEPS,
        guidance_scale: float = DEFAULT_GUIDANCE,
        strength: float = 0.85,
        seed: Optional[int] = None,
        scheduler: str = "euler_a",
        num_images: int = 1,
        mask_blur: int = 4,
        lora_name: Optional[str] = None,
        lora_scale: float = 0.8,
        source_filename: Optional[str] = None,
    ) -> dict:
        started = time.perf_counter()
        results = []

        try:
            inpaint_pipe = self._load_inpaint_pipeline()

            source_w, source_h = image.size
            width = width or self._round_down_8(min(source_w, DEFAULT_WIDTH))
            height = height or self._round_down_8(min(source_h, DEFAULT_HEIGHT))
            self.validate_dimensions(width, height)

            steps = max(1, min(steps, MAX_STEPS))
            num_images = max(1, min(num_images, MAX_BATCH))
            strength = max(0.01, min(float(strength), 0.99))
            mask_blur = max(0, min(int(mask_blur), 64))
            seed = self._new_seed(seed)

            image = self.resize_image(image, width, height, mode="fit")
            mask = self.prepare_mask(mask, (width, height), blur=mask_blur)

            self.set_scheduler(inpaint_pipe, scheduler)

            with self._lora_context(inpaint_pipe, lora_name, lora_scale):
                for index in range(num_images):
                    current_seed = (seed + index) % (2**32)
                    generator = self._generator(current_seed)

                    with torch.inference_mode():
                        output = inpaint_pipe(
                            prompt=prompt,
                            negative_prompt=negative_prompt or None,
                            image=image,
                            mask_image=mask,
                            width=width,
                            height=height,
                            strength=strength,
                            num_inference_steps=steps,
                            guidance_scale=guidance_scale,
                            generator=generator,
                            output_type="pil",
                        )

                    result_image = output.images[0]
                    results.append(
                        self._save_result(
                            result_image,
                            mode="inpaint",
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=width,
                            height=height,
                            steps=steps,
                            guidance_scale=guidance_scale,
                            strength=strength,
                            seed=current_seed,
                            scheduler=scheduler,
                            lora_name=lora_name,
                            lora_scale=lora_scale,
                            source_filename=source_filename,
                        )
                    )

                    del output, result_image, generator
                    gc.collect()
                    torch.cuda.empty_cache()

            elapsed = round(time.perf_counter() - started, 3)
            return {
                "success": True,
                "count": len(results),
                "elapsed_seconds": elapsed,
                "results": results,
                "gpu_memory": self._cuda_memory(),
            }
        finally:
            # The inpainting checkpoint is intentionally not kept resident on an
            # 8 GB system. Restore the base model for normal txt2img/img2img work.
            self._release_inpaint_pipeline()
            self._restore_base_pipeline()

    # =========================================================
    # LOCAL FILES / MODELS
    # =========================================================

    def list_loras(self) -> list[dict]:
        items = []
        for path in sorted(LORA_DIR.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".safetensors", ".pt", ".bin"}:
                continue

            items.append(
                {
                    "name": path.name,
                    "size_mb": round(path.stat().st_size / 1024**2, 2),
                }
            )
        return items

    def info(self) -> dict:
        props = torch.cuda.get_device_properties(0)
        return {
            "model": str(self.model_path),
            "model_exists": self.model_path.exists(),
            "inpaint_model": str(self.inpaint_model_path) if self.inpaint_model_path else None,
            "inpaint_model_exists": (
                self.inpaint_model_path.exists()
                if self.inpaint_model_path
                else False
            ),
            "gpu": torch.cuda.get_device_name(0),
            "vram_total_gb": round(props.total_memory / 1024**3, 2),
            "cuda_runtime": torch.version.cuda,
            "torch": torch.__version__,
            "diffusers": __import__("diffusers").__version__,
            "offload_mode": OFFLOAD_MODE,
            "dtype": "float32",
            "base_unet_in_channels": self.pipe.unet.config.in_channels,
            "lora_count": len(self.list_loras()),
            "supported_schedulers": self.SUPPORTED_SCHEDULERS,
            "defaults": {
                "width": DEFAULT_WIDTH,
                "height": DEFAULT_HEIGHT,
                "steps": DEFAULT_STEPS,
                "guidance_scale": DEFAULT_GUIDANCE,
                "strength": DEFAULT_STRENGTH,
                "max_width": MAX_WIDTH,
                "max_height": MAX_HEIGHT,
                "max_steps": MAX_STEPS,
                "max_batch": MAX_BATCH,
            },
            "gpu_memory": self._cuda_memory(),
        }
