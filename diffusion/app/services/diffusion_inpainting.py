# import gc
# import os
# import threading
# import time

# import torch

# from diffusers import (
#     StableDiffusionPipeline,
#     AutoPipelineForImage2Image,
#     StableDiffusionInpaintPipeline,
# )

# from PIL import Image
# from app.core.config import (
#     MODEL_PATH,
#     INPAINT_MODEL_PATH,
# )

# class DiffusionInpaintingService:
#     def __init__(self):
#         # =====================================================
#         # NORMAL MODEL
#         # =====================================================
#         self.pipe: StableDiffusionPipeline | None = None
#         self.image2image_pipe = None
#         # =====================================================
#         # INPAINTING MODEL
#         # =====================================================

#         self.inpaint_pipe: StableDiffusionInpaintPipeline | None = None
#         # =====================================================
#         # LOCK
#         # =====================================================

#         # Satu generation pada satu waktu.
#         self.lock = threading.Lock()

#     # =========================================================
#     # MEMORY MANAGEMENT
#     # =========================================================

#     def unload_normal_models(self):

#         print()
#         print("=" * 60)
#         print("UNLOADING NORMAL MODELS")
#         print("=" * 60)

#         if self.image2image_pipe is not None:

#             del self.image2image_pipe
#             self.image2image_pipe = None

#         if self.pipe is not None:

#             del self.pipe
#             self.pipe = None

#         gc.collect()

#         print("Normal models berhasil dilepas dari memory.")
#         print("=" * 60)

#     def unload_inpaint_model(self):

#         print()
#         print("=" * 60)
#         print("UNLOADING INPAINTING MODEL")
#         print("=" * 60)

#         if self.inpaint_pipe is not None:

#             del self.inpaint_pipe
#             self.inpaint_pipe = None

#         gc.collect()
#         print("Inpainting model berhasil dilepas dari memory.")
#         print("=" * 60)

#     # =========================================================
#     # LOAD NORMAL MODEL
#     # =========================================================

#     def load_model(self):
#         # Kalau inpainting sedang loaded,
#         # lepaskan terlebih dahulu.
#         if self.inpaint_pipe is not None:
#             self.unload_inpaint_model()
#         if self.pipe is not None:
#             return
#         if not os.path.exists(MODEL_PATH):
#             raise FileNotFoundError(
#                 f"Model tidak ditemukan: {MODEL_PATH}"
#             )
#         print()
#         print("=" * 60)
#         print("LOADING STABLE DIFFUSION")
#         print("=" * 60)
#         print(f"Model : {MODEL_PATH}")
#         print("Device: CPU")
#         start_time = time.time()
#         self.pipe = StableDiffusionPipeline.from_single_file(
#             MODEL_PATH,
#             torch_dtype=torch.float32,
#         )
#         self.pipe = self.pipe.to("cpu")
#         self.pipe.set_progress_bar_config(
#             disable=False
#         )
#         elapsed = time.time() - start_time
#         print(
#             f"Model berhasil dimuat "
#             f"dalam {elapsed:.2f} detik"
#         )
#         print("=" * 60)

#     # =========================================================
#     # LOAD IMAGE TO IMAGE
#     # =========================================================

#     def load_image2image_pipeline(self):
#         if self.pipe is None:
#             self.load_model()
#         if self.image2image_pipe is not None:
#             return
#         print()
#         print("=" * 60)
#         print("CREATING IMAGE TO IMAGE PIPELINE")
#         print("=" * 60)
#         start_time = time.time()
#         self.image2image_pipe = (
#             AutoPipelineForImage2Image.from_pipe(
#                 self.pipe
#             )
#         )
#         self.image2image_pipe.set_progress_bar_config(
#             disable=False
#         )
#         elapsed = time.time() - start_time
#         print(
#             f"Image-to-Image pipeline siap "
#             f"dalam {elapsed:.2f} detik"
#         )

#         print("=" * 60)

#     # =========================================================
#     # LOAD INPAINTING
#     # =========================================================

#     def load_inpaint_pipeline(self):
#         # Kalau model normal masih ada,
#         # lepaskan terlebih dahulu agar RAM tidak penuh.
#         if self.pipe is not None:
#             self.unload_normal_models()

#         if self.inpaint_pipe is not None:
#             return
#         if not os.path.exists(INPAINT_MODEL_PATH):
#             raise FileNotFoundError(
#                 "Model inpainting tidak ditemukan: "
#                 f"{INPAINT_MODEL_PATH}"
#             )
#         print()
#         print("=" * 60)
#         print("LOADING INPAINTING MODEL")
#         print("=" * 60)
#         print(
#             f"Model : {INPAINT_MODEL_PATH}"
#         )
#         print("Device: CPU")
#         start_time = time.time()
#         self.inpaint_pipe = (
#             StableDiffusionInpaintPipeline.from_single_file(
#                 INPAINT_MODEL_PATH,
#                 torch_dtype=torch.float32,
#             )
#         )
#         self.inpaint_pipe = (
#             self.inpaint_pipe.to("cpu")
#         )
#         self.inpaint_pipe.set_progress_bar_config(
#             disable=False
#         )
#         elapsed = time.time() - start_time
#         print(
#             f"Inpainting model berhasil dimuat "
#             f"dalam {elapsed:.2f} detik"
#         )
#         print("=" * 60)

#     # =========================================================
#     # TEXT TO IMAGE
#     # =========================================================

#     def generate_text_to_image(
#         self,
#         prompt: str,
#         negative_prompt: str | None = None,
#         width: int = 512,
#         height: int = 512,
#         num_inference_steps: int = 20,
#         guidance_scale: float = 7.5,
#         seed: int | None = None,
#     ):

#         self.load_model()
#         if seed is None:
#             seed = torch.randint(
#                 0,
#                 2**32 - 1,
#                 (1,),
#             ).item()
#         generator = torch.Generator(
#             device="cpu"
#         ).manual_seed(seed)

#         print()
#         print("=" * 60)
#         print("TEXT TO IMAGE")
#         print("=" * 60)

#         print(f"Prompt      : {prompt}")
#         print(f"Negative    : {negative_prompt}")
#         print(f"Resolution  : {width}x{height}")
#         print(f"Steps       : {num_inference_steps}")
#         print(f"Guidance    : {guidance_scale}")
#         print(f"Seed        : {seed}")
#         start_time = time.time()
#         with self.lock:
#             result = self.pipe(
#                 prompt=prompt,
#                 negative_prompt=negative_prompt,
#                 width=width,
#                 height=height,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=guidance_scale,
#                 generator=generator,
#             )
#         image = result.images[0]
#         elapsed = time.time() - start_time
#         print(
#             f"Generation selesai: "
#             f"{elapsed:.2f} detik"
#         )
#         print("=" * 60)
#         return image, seed

#     # =========================================================
#     # IMAGE TO IMAGE
#     # =========================================================

#     def generate_image_to_image(
#         self,
#         image: Image.Image,
#         prompt: str,
#         negative_prompt: str | None = None,
#         strength: float = 0.75,
#         num_inference_steps: int = 20,
#         guidance_scale: float = 7.5,
#         seed: int | None = None,
#         width: int = 512,
#         height: int = 512,
#     ):

#         self.load_image2image_pipeline()
#         if seed is None:
#             seed = torch.randint(
#                 0,
#                 2**32 - 1,
#                 (1,),
#             ).item()

#         generator = torch.Generator(
#             device="cpu"
#         ).manual_seed(seed)
#         image = image.convert("RGB")
#         image = image.resize(
#             (width, height)
#         )

#         print()
#         print("=" * 60)
#         print("IMAGE TO IMAGE")
#         print("=" * 60)
#         print(f"Prompt      : {prompt}")
#         print(f"Negative    : {negative_prompt}")
#         print(f"Strength    : {strength}")
#         print(f"Resolution  : {width}x{height}")
#         print(f"Steps       : {num_inference_steps}")
#         print(f"Guidance    : {guidance_scale}")
#         print(f"Seed        : {seed}")
#         start_time = time.time()
#         with self.lock:
#             result = self.image2image_pipe(
#                 prompt=prompt,
#                 negative_prompt=negative_prompt,
#                 image=image,
#                 strength=strength,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=guidance_scale,
#                 generator=generator,
#             )
#         output_image = result.images[0]
#         elapsed = time.time() - start_time
#         print(
#             f"Generation selesai: "
#             f"{elapsed:.2f} detik"
#         )
#         print("=" * 60)
#         return output_image, seed

#     # =========================================================
#     # INPAINTING
#     # =========================================================

#     def generate_inpainting(
#         self,
#         image: Image.Image,
#         mask_image: Image.Image,
#         prompt: str,
#         negative_prompt: str | None = None,
#         strength: float = 0.8,
#         num_inference_steps: int = 20,
#         guidance_scale: float = 7.5,
#         seed: int | None = None,
#         width: int = 512,
#         height: int = 512,
#     ):
#         self.load_inpaint_pipeline()
#         if seed is None:
#             seed = torch.randint(
#                 0,
#                 2**32 - 1,
#                 (1,),
#             ).item()
#         generator = torch.Generator(
#             device="cpu"
#         ).manual_seed(seed)

#         # =====================================================
#         # PREPARE ORIGINAL IMAGE
#         # =====================================================

#         image = image.convert("RGB")
#         image = image.resize(
#             (width, height)
#         )

#         # =====================================================
#         # PREPARE MASK
#         # =====================================================

#         # L = grayscale
#         #
#         # WHITE (255) = area yang akan diubah
#         # BLACK (0)   = area yang dipertahankan

#         mask_image = mask_image.convert("L")
#         mask_image = mask_image.resize(
#             (width, height),
#             Image.Resampling.NEAREST,
#         )

#         print()
#         print("=" * 60)
#         print("INPAINTING")
#         print("=" * 60)

#         print(f"Prompt      : {prompt}")
#         print(f"Negative    : {negative_prompt}")
#         print(f"Strength    : {strength}")
#         print(f"Resolution  : {width}x{height}")
#         print(f"Steps       : {num_inference_steps}")
#         print(f"Guidance    : {guidance_scale}")
#         print(f"Seed        : {seed}")
#         start_time = time.time()

#         with self.lock:
#             result = self.inpaint_pipe(
#                 prompt=prompt,
#                 negative_prompt=negative_prompt,
#                 image=image,
#                 mask_image=mask_image,
#                 strength=strength,
#                 num_inference_steps=num_inference_steps,
#                 guidance_scale=guidance_scale,
#                 generator=generator,
#             )
#         output_image = result.images[0]
#         elapsed = time.time() - start_time
#         print(
#             f"Generation selesai: "
#             f"{elapsed:.2f} detik"
#         )
#         print("=" * 60)
#         return output_image, seed

# diffusion_service = DiffusionInpaintingService()