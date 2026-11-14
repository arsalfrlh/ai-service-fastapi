import os
from dotenv import load_dotenv

load_dotenv()

APP_HOST = os.getenv(key="", default="127.0.0.1")
APP_PORT = int(os.getenv(key="APP_PORT", default="8000"))
MODEL_PATH = os.getenv(key="MODEL_PATH", default="E:/model/nmt/madlad400")
DEVICE = os.getenv(key="DEVICE", default="cpu")
COMPUTE_TYPE=  os.getenv(key="COMPUTE_TYPE", default="int8")
INTER_THREADS = int(os.getenv(key="INTER_THREADS", default="1"))
INTRA_THREADS = int(os.getenv(key="INTRA_THREADS", default="4"))