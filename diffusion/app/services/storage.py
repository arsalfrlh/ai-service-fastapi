import io
from datetime import timedelta
import uuid
from minio import Minio
from app.core.config import MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_BUCKET, MINIO_SECRET_KEY, MINIO_SECURE

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
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            print("Membuat bucket")
        else:
            print(f"Bucket tersedia: {self.bucket}")

    def upload_image(self, image):
        object_name = f"generated/{str(uuid.uuid4())}.png"
        image_buffer = io.BytesIO()
        image.save(image_buffer, format="PNG")
        image_buffer.seek(0)
        image_data = image_buffer.getvalue()

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=io.BytesIO(image_data),
            length=len(image_data),
            content_type="image/png"
        )

        url = self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=object_name,
            expires=timedelta(hours=1)
        )

        return {
            "file_name": object_name,
            "file_url": url
        }

storage_service = StorageService()