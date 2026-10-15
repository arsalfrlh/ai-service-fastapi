from fastapi import APIRouter, Header
from app.schemas.song import SongRequest
from starlette.concurrency import run_in_threadpool
from app.core.config import API_KEY
from app.schemas.response import responseFormat
from app.services.storage_service import storage_service
from app.services.whisper_service import whisper_service
import os

router = APIRouter(prefix="/api")

@router.post("/convert")
async def convert_lyric(request: SongRequest, kwanzx_key: str = Header(...)):
    if kwanzx_key != API_KEY:
        return responseFormat(success=False,status_code=401,message="Invalid API Key")
    try:
        file_path = await run_in_threadpool(
            storage_service.download,
            object_path=request.file_path
        )
        data = await run_in_threadpool(
            whisper_service.transcribe_audio,
            file_path=file_path,
            language=request.language,
            include_words=request.include_words
        )
        return responseFormat(success=True, status_code=200, message="Convert Lyric berhasil", data=data)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)