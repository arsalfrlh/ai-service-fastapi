from app.core.config import MINIO_ACCESS_KEY, MINIO_BUCKET, MINIO_ENDPOINT, MINIO_SECRET_KEY, MINIO_SECURE
from minio import Minio
import tempfile
import os

class StorageService:
    def __init__(self):
        self.client = Minio(
            endpoint=MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=MINIO_SECURE
        )
        self.bucket = MINIO_BUCKET

    def initialize(self):
        if not self.client.bucket_exists(bucket_name=self.bucket):
            self.client.make_bucket(bucket_name=self.bucket)
            print("Membuat bucket")
        else:
            print("Bucket sudah tersedia")

    def download(self, object_path: str):
        extension = os.path.splitext(object_path)[1]
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=extension
        )
        temp_file.close()
        self.client.fget_object(
            bucket_name=self.bucket,
            object_name=object_path,
            file_path=temp_file.name
        )
        return temp_file.name

storage_service = StorageService()