from fastapi import FastAPI, UploadFile, HTTPException
import os
import shutil
from faster_whisper import WhisperModel
import uuid
import soundfile as sf
from kokoro_onnx import Kokoro
from pydantic import BaseModel

app = FastAPI()
whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

kokoro = Kokoro(
    model_path="models/kokoro-v1.0.int8.onnx",
    voices_path="models/voices-v1.0.bin"
)

SONG_FOLDER="audio"
STT_FOLDER = os.path.join(SONG_FOLDER,"stt")
TTS_FOLDER = os.path.join(SONG_FOLDER,"tts")
ALLOWED_EXTENSION = {
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/ogg": ".ogg",
    "audio/flac": ".flac",
    "audio/x-aac": ".aac",
    "audio/aac": ".aac",
}

@app.post("/stt")
def convert_to_text(audio: UploadFile):
    try:
        if(audio.content_type not in ALLOWED_EXTENSION):
            raise HTTPException(
                status_code=400,
                detail=f"{audio.filename} tidak di dukung"
            )

        extension = ALLOWED_EXTENSION[audio.content_type]
        filename = f"{uuid.uuid4()}{extension}"
        audioPath = os.path.join(STT_FOLDER,filename)
        with open(audioPath, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
    
        segments, info = whisper.transcribe(
            audioPath,
            beam_size=5
        )
    
        text = ""
        for segment in segments:
            text += segment.text

        return{
            "success": True,
            "message": "Konvert berhasil",
            "data": text
        }
    except ValueError as e:
        return{
            "success": False,
            "message": e
        }

class TeksSpechRequest(BaseModel):
    keyword: str

@app.post("/tts")
def convert_to_spech(request: TeksSpechRequest):
    try:
        audio, sample_rate = kokoro.create(
            text=request.keyword,
            voice="af_sarah",
            speed=1.0,
            lang="en-us"
        )

        file_name = f"{uuid.uuid4()}.wav"
        audioPath = os.path.join(TTS_FOLDER, file_name)
        sf.write(audioPath, audio, sample_rate)
        return {
            "success": True,
            "message": "Konvert ke spech berhasil",
            "data": audioPath
        }
    except ValueError as e:
        return{
            "success": False,
            "message": e
        }