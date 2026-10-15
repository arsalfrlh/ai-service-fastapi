from app.schemas.response import responseFormat
from fastapi import Request, FastAPI
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.services.whisper_service import whisper_service
from app.services.storage_service import storage_service
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("AI Service starting")
    storage_service.initialize()
    whisper_service.load_model()
    print("AI Service running")
    yield
    print("AI Service shutdown.")

app = FastAPI(
    lifespan=lifespan,
    version="1.0.0",
    title="AI Service lyric"
)

@app.exception_handler(RequestValidationError)
async def request_exception(request: Request, exc: RequestValidationError):
    return responseFormat(success=False, message=exc.errors(), status_code=422)

app.include_router(router=router)