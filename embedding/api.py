from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from typing import Any, Optional
from embedding_service import EmbeddingService
from pydantic import BaseModel
from PIL import Image
from io import BytesIO
from pathlib import Path

app = FastAPI()
embedding_service = EmbeddingService()

@app.exception_handler(RequestValidationError)
def request_validation(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        error = error.copy()
        if "input" in error:
            value = error["input"]
            if isinstance(value, bytes):
                error["input"] = (
                    f"<bytes: {len(value)}>"
                )
        if "ctx" in error:
            error["ctx"] = str(error["ctx"])
        errors.append(error)
    return JSONResponse(
        status_code=422,
        content={
            "message": errors,
            "success": False
        }
    )

@app.get("/")
def root():
    return {
        "message": "Qwen3-VL Embedding API",
        "status": "running"
    }

class EmbedTextRequest(BaseModel):
    text: str

@app.post("/embed/text")
def embed_text(request: EmbedTextRequest):
    embed = embedding_service.embed_text(request.text)
    data = {
        "type": "text",
        "text": request.text,
        "dimension": len(embed),
        "vector": embed
    }
    return responseFormat(message="Embedd Text Success", success=True, data=data)

@app.post("/embed/image")
async def embed_image(image: UploadFile = File(...)):
    content = await image.read()
    pil_image = Image.open(BytesIO(content)).convert("RGB")
    embed = embedding_service.embed_image(pil_image)
    data = {
        "type": "image",
        "image_name": image.filename,
        "dimension": len(embed),
        "vector": embed
    }
    return responseFormat("Embed Image Success", success=True, data=data)

class EmbedMultiRequest(BaseModel):
    message: str = Form(...)
    image: UploadFile = File(...)

@app.post("/embed/screenshot")
async def embed_screenshot(image: UploadFile = File(...), instruction: Optional[str] = Form(None)):
    content = await image.read()
    screenshot = Image.open(BytesIO(content)).convert("RGB")
    vector = embedding_service.embed_screenshot(image=screenshot,instruction=instruction)
    data = {
        "type": "screenshot",
        "image_name": image.filename,
        "dimension": len(vector),
        "vector": vector
    }
    return responseFormat(
        message="Embed Screenshot Success",
        success=True,
        data=data
    )


# ==========================================================
# VIDEO
# ==========================================================

@app.post("/embed/video")
async def embed_video(video: UploadFile = File(...), instruction: Optional[str] = Form(None), fps: Optional[float] = Form(None), max_frames: Optional[int] = Form(None)):
    # Simpan video ke temporary file karena processor
    # Qwen dapat memproses file video/path.
    extension = Path(video.filename or "video.mp4").suffix
    temp_path = (
        Path.cwd()
        / f"_temp_embedding{extension}"
    )

    try:
        content = await video.read()
        temp_path.write_bytes(content)
        vector = embedding_service.embed_video(video=str(temp_path),instruction=instruction,fps=fps,max_frames=max_frames)
        data = {
            "type": "video",
            "video_name": video.filename,
            "dimension": len(vector),
            "vector": vector
        }
        return responseFormat(
            message="Embed Video Success",
            success=True,
            data=data
        )
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ==========================================================
# MULTIMODAL TEXT + IMAGE
# ==========================================================

@app.post("/embed/multi")
async def embed_multi(text: str = Form(...), image: UploadFile = File(...), instruction: Optional[str] = Form(None)):
    content = await image.read()
    pil_image = Image.open(BytesIO(content)).convert("RGB")
    vector = embedding_service.embed_text_image(
        text=text,
        image=pil_image,
        instruction=instruction
    )
    data = {
        "type": "text_image",
        "text": text,
        "image_name": image.filename,
        "dimension": len(vector),
        "vector": vector
    }
    return responseFormat(
        message="Embed Text And Image Success",
        success=True,
        data=data
    )

def responseFormat(message: str, success: bool, status_code: int = 200, data: Any = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "success": success,
            "data": data
        }
    )