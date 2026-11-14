from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.schemas.response import responseFormat
from app.services.translator_service import translator_service
from app.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting AI Service")
    translator_service.load_model()
    print("AI Service Running")
    yield
    print("AI Service shutdown")

app = FastAPI(
    lifespan=lifespan,
    title="AI Service",
    version="1.0.0"
)

@app.exception_handler(RequestValidationError)
async def request_validation(request: Request, exc: RequestValidationError):
    return responseFormat(success=False, status_code=422, message=exc.errors())

app.include_router(router=router)