from fastapi import APIRouter
from app.services.translator_service import translator_service
from app.schemas.response import responseFormat
from app.schemas.translate import TranslateRequest

router = APIRouter(
    prefix="/api"
)

@router.post("/translate")
async def translate(request: TranslateRequest):
    data = translator_service.translate(word=request.word, target_language=request.target_language)
    return responseFormat(success=True, status_code=200, message="Translate berhasil", data=data)