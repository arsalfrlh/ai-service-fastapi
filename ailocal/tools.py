from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from transformers import AutoProcessor, AutoModelForMultimodalLM, TextIteratorStreamer
import torch
from pydantic import BaseModel
from threading import Thread
import json

MODEL_PATH=r"C:\model\qwen"

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True
)

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True
)

model.eval()

print("\nModel berhasil dimuat!")
print("Device:", next(model.parameters()).device)
print("Ketik 'exit' untuk keluar.\n")

app = FastAPI()

@app.exception_handler(RequestValidationError)
def request_validation(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": exc.errors()
        }
    )

class MessageRequest(BaseModel):
    message: str

@app.post("/message")
def send_message(request: MessageRequest):
    return StreamingResponse(
        generate_chat(request),
        media_type="application/x-ndjson"
    )
    

def generate_chat(request: MessageRequest):
    messages = []
    messages.append({
        "role": "system",
        "content": [
            {
                "type": "text",
                "text": """
                    You are Kwanza AI, developed by Arsal Fahrulloh.
                """
            }
        ]
    })
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": request.message
            }
        ]
    })

    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = inputs.to(model.device)

    streamer = TextIteratorStreamer(
        processor.tokenizer,
        skip_prompt=True,
        skip_special_tokens=True
    )

    generation_kwargs = {
        **inputs,
        "streamer": streamer,
        "max_new_tokens": 256,
    }

    thread = Thread(
        target=model.generate,
        kwargs=generation_kwargs,
    )
    thread.start()

    full_content = ""
    for content in streamer:
        yield json.dumps({
            "message": {
                "role": "assistant",
                "content": content
            }
        }) + "\n"

        full_content += content

    yield json.dumps({
        "message": {
            "role": "assistant",
            "content": full_content
        }
    }) + "\n"