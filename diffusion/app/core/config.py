import os
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = os.getenv(key="MODEL_PATH",default=r"C:\model\diffusion\v1-5-pruned-emaonly.safetensors")
MINIO_ENDPOINT = os.getenv(key="MINIO_ENDPOINT", default="127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv(key="MINIO_ACCESS_KEY", default="minioadmin")
MINIO_SECRET_KEY = os.getenv(key="MINIO_SECRET_KEY", default="minioadmin")
MINIO_SECURE = os.getenv(key="MINIO_SECURE", default="false").lower() == "true"
MINIO_BUCKET = os.getenv(key="MINIO_BUCKET", default="diffusion")
APP_HOST = os.getenv(key="APP_HOST", default="127.0.0.1")
APP_PORT = int(os.getenv(key="APP_PORT", default="8000"))

# INPAINT_MODEL_PATH = os.getenv(
#     "INPAINT_MODEL_PATH",
#     r"C:\model\diffusion\inpainting\sd-v1-5-inpainting.ckpt",
# )