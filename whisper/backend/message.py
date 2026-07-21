from fastapi import FastAPI, WebSocket, UploadFile, File, HTTPException, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from ollama import chat
from pydantic import BaseModel
import json
import os
import shutil
import base64

HISTORY_FILE="history.json"

app = FastAPI()

IMAGE_FOLDER = "uploads/images"

ALLOWED_IMAGES = [
    "image/png",
    "image/jpeg",
    "image/jpg"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # untuk testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.websocket: WebSocket | None = None

    async def connect(self, websocket: WebSocket):
        self.websocket = websocket
        await websocket.accept()
        await websocket.send_json({
            "event": "connected",
            "data": {
                "message": "Webocket From FastAPI connected"
            }
        })

    async def send_broadcast(self, action: str, message: dict):
        if(self.websocket):
            await self.websocket.send_json({
                    "event": "message",
                    "data": {
                        "action": action,
                        "message": message
                    }
                })

    async def send_broadcast_ai(self, chunk: str, done: bool = False):
        if(self.websocket):
            await self.websocket.send_json({
                    "event": "ai-response",
                    "data": {
                        "chunk": chunk,
                        "done": done
                    }
                })

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_json() #receive data from user

    except WebSocketDisconnect:
        print("Client disconnected")

@app.get("/message")
def get_message():
    history = load_history()
    messages = []
    for message in history:
        if "assistant" == message['role'] or "user" == message['role']:
            messages.append(message)

    return {
        "success": True,
        "message": "Menampilkan semua pesan",
        "data": messages
    }

@app.post("/message")
async def send_message(question: str = Form(...), images: list[UploadFile] | None = File(None)):
    messages = []
    uploadImages = []
    uploadImagePaths = []
    history = load_history()
    message = {
        "role": "user",
        "content": question
    }

    if(images):
        for image in images:
            if image.content_type not in ALLOWED_IMAGES:
                raise HTTPException(
                    status_code=400,
                    detail=f"{image.filename} tidak di dukung"
                )
            imagePath = os.path.join(IMAGE_FOLDER,image.filename)
            uploadImagePaths.append(imagePath)
            with open(imagePath, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            with open(imagePath, "rb") as f:
                base64Image = base64.b64encode(f.read()).decode("utf-8")
                uploadImages.append(base64Image)
        message['images'] = uploadImages
                
    messages.extend(history)
    messages.append(message)
    await manager.send_broadcast("create", message)

    response = chat(
        model="qwen3.5:4b",
        stream=True,
        messages=messages
    )

    full_content = ""
    full_thinking = ""
    for chunk in response:
        if chunk.message.content:
            full_content += chunk.message.content
        if chunk.message.thinking:
            full_thinking += chunk.message.thinking
        await manager.send_broadcast_ai(chunk.message.content, chunk.done)

    messageAssistant = {
        "role": "assistant",
        "content": full_content
    }
    await manager.send_broadcast("create", messageAssistant)
    history.append(message)
    history.append(messageAssistant)
    save_data(history)
    return {
        "message": "Pesan berhasil dikirim",
        "success": True
    }


def load_history():
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w') as f:
            json.dump([], f)
        return []

    with open(HISTORY_FILE, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return []

def save_data(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, indent=4)