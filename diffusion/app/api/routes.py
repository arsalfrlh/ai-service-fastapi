from fastapi import APIRouter, UploadFile, File, Form
from starlette.concurrency import run_in_threadpool
from app.schemas.image import TextToImageRequest
from app.schemas.response import responseFormat
from app.services.diffusion import diffusion_service
from app.services.storage import storage_service
from io import BytesIO
from PIL import Image

router = APIRouter(prefix="/api")

@router.get("/health")
async def health():
    return responseFormat(
        success=True,
        data={
            "service": "AI Image Service",
            "model_loaded": diffusion_service.pipe is not None,
            "image2image_loaded": diffusion_service.image2image_pipe is not None,
            "inpainting_model_loaded": diffusion_service.inpaint_pipe is not None
        }
    )

@router.post("/image/text-to-image")
async def text_to_image(request: TextToImageRequest):
    try:
        image, seed = await run_in_threadpool(
            diffusion_service.generate_text_to_image, #function dari service diffuser
            prompt=request.prompt, #semua parameter dari function generate_text_to_image
            negative_prompt=request.negative_prompt,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed
        )

        storage_result = await run_in_threadpool(
            storage_service.upload_image,
            image=image
        )

        data = {
            "image": storage_result,
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "width": request.width,
            "height": request.height,
            "num_inference_steps": request.num_inference_steps,
            "guidance_scale": request.guidance_scale,
            "seed": seed,
        }

        return responseFormat(success=True, status_code=201, message="Image berhasil dibuat", data=data)
    except Exception as e:
        return responseFormat(success=False, status_code=500, message=str(e))

@router.post("/image/image-to-image")
async def image_to_image(
    image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str | None = Form(default=None),
    strength: float = Form(default=0.75, ge=0.0, le=1.0),
    num_inference_steps: int = Form(default=20, ge=1, le=50),
    guidance_scale: float = Form(default=7.5, ge=1.0, le=20),
    seed: int | None = Form(default=None),
    width: int = Form(default=512, ge=256, le=768),
    height: int = Form(default=512, ge=256, le=768)
):
    allowed_type = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
    if image.content_type not in allowed_type:
        return responseFormat(success=False, status_code=400, message="Format gambar tidak didukung")
    image_bytes = await image.read()
    if not image_bytes:
        return responseFormat(success=False, status_code=400, message="File gambar kosong")

    try:
        input_image = Image.open(BytesIO(image_bytes))
        input_image.load()
        input_image = input_image.convert("RGB")

        output_image, seed = await run_in_threadpool(
            diffusion_service.generate_image_to_image,
            image=input_image,
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            width=width,
            height=height
        )

        storage_result = await run_in_threadpool(
            storage_service.upload_image,
            image=output_image
        )

        data = {
            "image": storage_result,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "strength": strength,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed
        }
        return responseFormat(success=True, status_code=201, message="Image berhasil digenerate", data=data)
    except Exception as e:
        return responseFormat(success=False, status_code=500, message=str(e))
    
@router.post("/image/inpainting-image")
async def inpainting_image(
    image: UploadFile = File(...),
    mask_image: UploadFile = File(...),
    prompt: str = Form(...),
    negative_prompt: str | None = Form(default=None),
    strength: float = Form(default=0.75, ge=0.0, le=1.0),
    num_inference_steps: int = Form(default=20, ge=1, le=50),
    guidance_scale: float = Form(default=7.5, ge=1.0, le=20),
    seed: int | None = Form(default=None),
    width: int = Form(default=512, ge=256, le=768),
    height: int = Form(default=512, ge=256, le=768)
):
    allowed_type = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
    if image.content_type not in allowed_type or mask_image.content_type not in allowed_type:
        return responseFormat(success=False, status_code=400, message="Format gambar tidak didukung")
    image_bytes = await image.read()
    mask_bytes = await mask_image.read()
    if not image_bytes or not mask_bytes:
        return responseFormat(success=False, status_code=400, message="File gambar kosong")

    try:
        input_image = Image.open(BytesIO(image_bytes))
        input_image.load()
        input_image = input_image.convert("RGB")

        input_mask = Image.open(BytesIO(mask_bytes))
        input_mask.load()
        input_mask = input_mask.convert("L")

        output_image, seed = await run_in_threadpool(
            diffusion_service.generate_inpainting_image,
            image=input_image,
            mask_image=input_mask,
            prompt=prompt,
            negative_prompt=negative_prompt,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
            width=width,
            height=height
        )

        storage_result = await run_in_threadpool(
            storage_service.upload_image,
            image=output_image
        )

        data = {
            "image": storage_result,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "strength": strength,
            "width": width,
            "height": height,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "seed": seed
        }
        return responseFormat(success=True, status_code=201, message="Image berhasil digenerate", data=data)
    except Exception as e:
        return responseFormat(success=False, status_code=500, message=str(e))

# @router.post("/image/inpainting")
# async def inpainting(
#     image: UploadFile = File(...),
#     mask_image: UploadFile = File(...),
#     prompt: str = Form(...),
#     negative_prompt: str | None = Form(
#         default=None
#     ),
#     strength: float = Form(
#         default=0.8,
#         ge=0.0,
#         le=1.0,
#     ),
#     num_inference_steps: int = Form(
#         default=20,
#         ge=1,
#         le=50,
#     ),
#     guidance_scale: float = Form(
#         default=7.5,
#         ge=1.0,
#         le=20,
#     ),
#     seed: int | None = Form(
#         default=None
#     ),
#     width: int = Form(
#         default=512,
#         ge=256,
#         le=768,
#     ),
#     height: int = Form(
#         default=512,
#         ge=256,
#         le=768,
#     ),
# ):
#     allowed_type = {
#         "image/png",
#         "image/jpeg",
#         "image/jpg",
#         "image/webp",
#     }
#     # =========================================================
#     # VALIDATE ORIGINAL IMAGE
#     # =========================================================
#     if image.content_type not in allowed_type:
#         return responseFormat(
#             success=False,
#             status_code=400,
#             message="Format gambar tidak didukung",
#         )
#     # =========================================================
#     # VALIDATE MASK
#     # =========================================================
#     if mask_image.content_type not in allowed_type:
#         return responseFormat(
#             success=False,
#             status_code=400,
#             message="Format mask tidak didukung",
#         )
#     # =========================================================
#     # READ ORIGINAL IMAGE
#     # =========================================================
#     image_bytes = await image.read()
#     if not image_bytes:
#         return responseFormat(
#             success=False,
#             status_code=400,
#             message="File gambar kosong",
#         )
#     # =========================================================
#     # READ MASK
#     # =========================================================
#     mask_bytes = await mask_image.read()
#     if not mask_bytes:
#         return responseFormat(
#             success=False,
#             status_code=400,
#             message="File mask kosong",
#         )
#     try:
#         # =====================================================
#         # OPEN ORIGINAL IMAGE
#         # =====================================================
#         input_image = Image.open(
#             BytesIO(image_bytes)
#         )
#         input_image.load()
#         input_image = input_image.convert(
#             "RGB"
#         )
#         # =====================================================
#         # OPEN MASK
#         # =====================================================
#         input_mask = Image.open(
#             BytesIO(mask_bytes)
#         )
#         input_mask.load()
#         input_mask = input_mask.convert(
#             "L"
#         )
#         # =====================================================
#         # IMPORTANT:
#         # ORIGINAL IMAGE & MASK SHOULD HAVE SAME SIZE
#         # =====================================================
#         if input_image.size != input_mask.size:
#             return responseFormat(
#                 success=False,
#                 status_code=400,
#                 message=(
#                     "Ukuran image dan mask harus sama"
#                 ),
#             )
#         # =====================================================
#         # GENERATE
#         # =====================================================
#         result_image, generated_seed = (
#             await run_in_threadpool(
#                 diffusion_service.generate_inpainting,
#                 image=input_image,
#                 mask_image=input_mask,
#                 prompt=prompt,
#                 negative_prompt=negative_prompt,
#                 strength=strength,
#                 num_inference_steps=(
#                     num_inference_steps
#                 ),
#                 guidance_scale=guidance_scale,
#                 seed=seed,
#                 width=width,
#                 height=height,
#             )
#         )
#         # =====================================================
#         # UPLOAD TO MINIO
#         # =====================================================
#         storage_result = await run_in_threadpool(
#             storage_service.upload_image,
#             image=result_image,
#         )
#         # =====================================================
#         # RESPONSE
#         # =====================================================
#         data = {
#             "image": storage_result,
#             "prompt": prompt,
#             "negative_prompt": negative_prompt,
#             "strength": strength,
#             "width": width,
#             "height": height,
#             "num_inference_steps": (
#                 num_inference_steps
#             ),
#             "guidance_scale": guidance_scale,
#             "seed": generated_seed,
#             "input_image": {
#                 "file_name": image.filename,
#                 "content_type": image.content_type,
#             },
#             "mask_image": {
#                 "file_name": mask_image.filename,
#                 "content_type": mask_image.content_type,
#             },
#         }
#         return responseFormat(
#             success=True,
#             status_code=201,
#             message="Image berhasil di-inpaint",
#             data=data,
#         )
#     except Exception as e:
#         return responseFormat(
#             success=False,
#             status_code=500,
#             message=str(e),
#         )