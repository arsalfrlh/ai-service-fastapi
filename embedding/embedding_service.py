import sys
from pathlib import Path
from typing import Optional
import torch
from scripts.src.models.qwen3_vl_embedding import Qwen3VLEmbedder

MODEL_PATH = Path(r"E:\model\embedding\Qwen3-VL-Embedding-2B")

sys.path.insert(0,str(MODEL_PATH))


class EmbeddingService:
    def __init__(self):
        print("=" * 60)
        print("Initializing Qwen3-VL Embedding")
        print("=" * 60)
        print("Model:", MODEL_PATH)
        print("CUDA available:", torch.cuda.is_available())
        if torch.cuda.is_available():
            print(
                "GPU:",
                torch.cuda.get_device_name(0)
            )
        self.model = Qwen3VLEmbedder(
            model_name_or_path=str(MODEL_PATH),
            torch_dtype=torch.float32
        )
        self.model.model.eval()
        print("=" * 60)
        print("Qwen3-VL Embedding loaded")
        print("=" * 60)

    # ======================================================
    # TEXT
    # ======================================================

    @torch.inference_mode()
    def embed_text(self, text: str):
        if not text or not text.strip():
            raise ValueError(
                "Text cannot be empty."
            )
        inputs = [
            {
                "text": text
            }
        ]
        return self._process(inputs)

    # ======================================================
    # IMAGE
    # ======================================================

    @torch.inference_mode()
    def embed_image(self, image, instruction: Optional[str] = None):
        item = {
            "image": image
        }
        if instruction:
            item["instruction"] = instruction
        return self._process([item])

    # ======================================================
    # SCREENSHOT
    # ======================================================

    @torch.inference_mode()
    def embed_screenshot(self, image, instruction: Optional[str] = None):
        # Screenshot diperlakukan sebagai image.
        return self.embed_image(
            image=image,
            instruction=instruction
        )

    # ======================================================
    # VIDEO
    # ======================================================

    @torch.inference_mode()
    def embed_video(self, video, instruction: Optional[str] = None, fps: Optional[float] = None, max_frames: Optional[int] = None):
        item = {
            "video": video
        }
        if instruction:
            item["instruction"] = instruction
        if fps is not None:
            item["fps"] = fps
        if max_frames is not None:
            item["max_frames"] = max_frames
        return self._process([item])

    # ======================================================
    # TEXT + IMAGE
    # ======================================================

    @torch.inference_mode()
    def embed_text_image(self, text: str, image, instruction: Optional[str] = None):
        item = {
            "text": text,
            "image": image
        }
        if instruction:
            item["instruction"] = instruction
        return self._process([item])

    # ======================================================
    # TEXT + VIDEO
    # ======================================================

    @torch.inference_mode()
    def embed_text_video(self, text: str, video, instruction: Optional[str] = None, fps: Optional[float] = None, max_frames: Optional[int] = None):
        item = {
            "text": text,
            "video": video
        }
        if instruction:
            item["instruction"] = instruction
        if fps is not None:
            item["fps"] = fps
        if max_frames is not None:
            item["max_frames"] = max_frames
        return self._process([item])

    # ======================================================
    # GENERIC MULTIMODAL
    # ======================================================

    @torch.inference_mode()
    def embed_multimodal(self, text: Optional[str] = None, image=None, video=None, instruction: Optional[str] = None, fps: Optional[float] = None, max_frames: Optional[int] = None):
        item = {}
        if text:
            item["text"] = text
        if image is not None:
            item["image"] = image
        if video is not None:
            item["video"] = video
        if instruction:
            item["instruction"] = instruction
        if fps is not None:
            item["fps"] = fps
        if max_frames is not None:
            item["max_frames"] = max_frames
        if not item:
            raise ValueError(
                "At least one modality is required."
            )
        return self._process([item])

    # ======================================================
    # INTERNAL PROCESS
    # ======================================================

    def _process(self, inputs):
        embeddings = self.model.process(inputs)
        embedding = embeddings[0]
        return embedding.tolist()


if __name__ == "__main__":
    service = EmbeddingService()
    print()
    print("Testing text embedding...")
    vector = service.embed_text(
        "Laravel is a PHP framework"
    )
    print()
    print("Dimension:", len(vector))
    print( "First 10:",vector[:10])