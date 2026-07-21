from fastapi import FastAPI, WebSocket, UploadFile, HTTPException
from kokoro_onnx import Kokoro
from faster_whisper import WhisperModel
import os
import shutil
import uuid
from ollama import chat
import asyncio
import re

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

client: WebSocket | None = None

UPLOAD_PATHS="uploads"
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

@app.post("/voice")
async def send_voice(voice: UploadFile):
    global client
    if(voice.content_type not in ALLOWED_EXTENSION):
        raise HTTPException(
            status_code=400,
            detail=f"{voice.content_type} tidak di dukung"
        )
    
    extension = ALLOWED_EXTENSION[voice.content_type]
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = os.path.join(UPLOAD_PATHS,file_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(voice.file, buffer)

    question = ""
    segments, info = whisper.transcribe(
        file_path,
        beam_size=5
    )

    for segment in segments:
        question += segment.text

    response = chat(
        model="qwen3.5:4b",
        stream=True,
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

    thinking = ""
    sentence  = ""
    for chunk in response:
        if chunk.message.content:
            sentence += chunk.message.content
        if chunk.message.thinking:
            thinking += chunk.message.thinking

        while True:
            match = re.search(r"[.!?]+[\s\n]*", sentence)

            if not match:
                break

            end = match.end()
            complete = sentence[:end].strip()
            sentence = sentence[end:]
            if client:
                await client.send_json({
                    "event": "text",
                    "data": complete
                })
            await send_audio(complete)

    if sentence.strip():
        await send_audio(sentence)

        if client:
            await client.send_json({
                "event": "text",
                "data": sentence
            })

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    global client
    await websocket.accept()
    client = websocket
    try:
        while True:
            data = await websocket.receive_json()

            if(data['event'] == "call"):
                await websocket.send_json({
                    "event": data['event'],
                    "data": "Halo ini dari Fastapi"
                })
    except ValueError as e:
        client = None
        print(e)

async def send_audio(text: str):
    global client
    if client is None:
        return
    
    audio, sample_rate = kokoro.create(
        text=text,
        voice="af_sarah",
        speed=1.0,
        lang="en-us"
    )

    await client.send_json({
        "event": "audio_start",
        "sample_rate": sample_rate,
        "channels": 1,
        "format": "float32"
    })

    chunk_size = 4096
    for i in range(0, len(audio), chunk_size):
        chunk = audio[i:i+chunk_size]
        await client.send_bytes(chunk.tobytes())
        await asyncio.sleep(0.005)

    await client.send_json({
        "event": "audio_end"
    })