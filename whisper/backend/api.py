from ollama import chat
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel
from fastapi import FastAPI, HTTPException, UploadFile
import uuid
import os
import shutil
import soundfile as sf

kokoro = Kokoro(
    model_path="models/kokoro-v1.0.int8.onnx",
    voices_path="models/voices-v1.0.bin"
)

whisper = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

app = FastAPI()

UPLOAD_PATHS="uploads"
OUTPUT_PATHS="outputs"

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

@app.post("/message")
def send_message(voice_record: UploadFile):
    try:
        if(voice_record.content_type not in ALLOWED_EXTENSION):
            raise HTTPException(
                status_code=400,
                detail=f"{voice_record.content_type} tidak di dukung"
            )
        extension = ALLOWED_EXTENSION[voice_record.content_type]
        filename = f"{uuid.uuid4()}{extension}"
        voicePath = os.path.join(UPLOAD_PATHS,filename)
        with open(voicePath, "wb") as buffer:
            shutil.copyfileobj(voice_record.file, buffer)
    
        question = ""
        segments, info = whisper.transcribe(
            voicePath,
            beam_size=5
        )
    
        for segment in segments:
            question += segment.text
    
        response = chat(
            model="qwen3.5:4b",
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": """
                        You are Kwanza AI, a local voice assistant created by Arsal Fahrulloh.
                        Your responses will be spoken aloud using a text-to-speech system.

                        Rules:

                        - Speak naturally like a real person.
                        - Keep answers concise.
                        - Usually answer in one to three short sentences.
                        - Never introduce yourself unless the user asks.
                        - Do not repeat unnecessary information.
                        - Avoid markdown, bullet points, emojis, or special formatting.
                        - Speak in a warm and friendly tone.
                        - If the answer is unknown, say so honestly.
                        - If tools are available, use them only when necessary.
                        - Answer directly instead of explaining your reasoning.
                    """
                },
                {
                    "role": "user",
                    "content": question
                }
            ]
        )
    
        audio, sample_rate = kokoro.create(
            text=response.message.content,
            voice="af_sarah",
            speed=1.0,
            lang="en-us"
        )
    
        file_name = f"{uuid.uuid4()}.wav"
        audio_path = os.path.join(OUTPUT_PATHS,file_name)
        sf.write(audio_path, audio, sample_rate)
        return{
            "success": True,
            "message": "Response AI",
            "data": audio_path
        }
    except ValueError as e:
        return{
            "success": False,
            "message": e
        }