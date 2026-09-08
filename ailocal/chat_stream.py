import torch
from threading import Thread
from transformers import AutoProcessor, AutoModelForMultimodalLM, TextIteratorStreamer

MODEL_PATH=r"C:\model\qwen"
print("Loading Process...")

processor = AutoProcessor.from_pretrained(
    MODEL_PATH,
    local_files_only=True
)

print("Loading model...")

model = AutoModelForMultimodalLM.from_pretrained(
    MODEL_PATH,
    dtype=torch.float32,
    local_files_only=True
)

model.eval()

print("\nModel berhasil dimuat!")
print("Device:", next(model.parameters()).device)
print("Ketik 'exit' untuk keluar.\n")

messages = []

while True:
    user_input = input("Anda: ")

    if user_input.lower() == "quit":
        break

    messages.append({
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": user_input
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

    print("Qwen: ", end="", flush=True)

    response = ""

    for text in streamer:
        print(text, end="", flush=True)
        response += text
    print("\n")

    thread.join()

    messages.append({
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": response,
            }
        ],
    })