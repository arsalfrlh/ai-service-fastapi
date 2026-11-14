from pydantic import BaseModel, Field

class TranslateRequest(BaseModel):
    target_language: str = Field(default="id", min_length=2, max_length=15)
    word: str = Field(min_length=1, max_length=5000)