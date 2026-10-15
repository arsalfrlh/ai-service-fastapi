import os
from dotenv import load_dotenv
load_dotenv()

MINIO_ENDPOINT = os.getenv(key="MINIO_ENDPOINT", default="127.0.0.1:9000")
MINIO_ACCESS_KEY = os.getenv(key="MINIO_ACCESS_KEY", default="minioadmin")
MINIO_SECRET_KEY = os.getenv(key="MINIO_SECRET_KEY", default="minioadmin")
MINIO_SECURE = os.getenv(key="MINIO_SECURE", default="false").lower() == "true"
MINIO_BUCKET = os.getenv(key="MINIO_BUCKET", default="diffusion")
APP_HOST = os.getenv(key="APP_HOST", default="127.0.0.1")
APP_PORT = int(os.getenv(key="APP_PORT", default="8000"))
WHISPER_DEVICE = os.getenv(key="WHISPER_DEVICE", default="cpu")
WHISPER_MODEL_SIZE = os.getenv(key="WHISPER_MODEL_SIZE", default="small")
WHISPER_COMPUTE_TYPE = os.getenv(key="WHISPER_COMPUTE_TYPE", default="int8")
# CPU_THREADS = int(os.getenv(key="DEFAULT_CPU_THREADS", default=str(max(1, (os.cpu_count() or 4) - 1))))
CPU_THREADS = max(1, (os.cpu_count() or 4) - 1)
API_KEY = os.getenv(key="API_KEY", default="kwanzxx-arsalfrlh")