from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from app.api.routes import router
from app.services.storage import storage_service
from app.services.diffusion import diffusion_service
from app.schemas.response import responseFormat

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("STARTING AI IMAGE SERVICE")
    print("=" * 60)
    storage_service.initialize()
    diffusion_service.load_model()
    print("AI Image Service siap.")
    print("=" * 60)
    yield
    print("AI Image Service shutdown.")

app = FastAPI(
    title="Local AI Image Generator",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(RequestValidationError)
async def exception_validation(request: Request, exc: RequestValidationError):
    return responseFormat(success=False, status_code=422, message=exc.errors())

app.include_router(router)