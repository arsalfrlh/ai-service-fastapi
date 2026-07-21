from fastapi import FastAPI, WebSocket

app = FastAPI()

@app.websocket("/ws")
async def connect_websocket(websocket: WebSocket):
    await websocket.accept() #terima koneksi websocket dari client
    await websocket.send_json({ #kirim data dari server ke client
        "event": "websocket:connected",
        "data": {}
    })

    try:
        while True:
            data = await websocket.receive_json() #menyimpan semua hasil data yg dikirim oleh client
            if(data['event'] == "call:client"):
                message = None
                if("data" in data and "message" in data['data']): #cek apakah ada array key "data" di variabel data| cek apakah ada array key "message" di variabel data["message"]
                    message = data['data']['message']
                await websocket.send_json({ #kirim data dari server ke client
                    "event": "call:server",
                    "data": {
                        "client": message,
                        "server": "Hello From Fast API"
                    }
                })

    except ValueError as e:
        print(e)