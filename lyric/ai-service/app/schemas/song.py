from pydantic import BaseModel

class SongRequest(BaseModel):
    id: int
    file_path: str
    language: str | None = None
    include_words: bool = True