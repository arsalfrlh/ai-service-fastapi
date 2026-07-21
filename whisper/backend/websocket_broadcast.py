from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
clients: list[WebSocket] = []

@app.websocket("/ws")
async def connect_websocket(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    await websocket.send_json({
        "event": "websocket:connected",
        "data": {}
    })

    for client in clients:
        await client.send_json({
            "event": "client:connected",
            "data": {
                "clients": len(clients)
            }
        })

    try:
        while True:
            data = await websocket.receive_json()
            if(data['event'] == "call:client"):
                message = None
                if("data" in data and "message" in data['data']):
                    message = data['data']['message']
                await websocket.send_json({
                    "event": "call:server",
                    "data": {
                        "client": message,
                        "server": "Hello From Fast API"
                    }
                })
    
            if(data['event'] == "call:broadcast"):
                message = None
                if("data" in data and "message" in data['data']):
                    message = data['data']['message']
    
                for client in clients:
                    await client.send_json({
                        "event": "client:broadcast",
                        "data": {
                            "message": message
                        }
                    })

    except WebSocketDisconnect:
        clients.remove(websocket)

    except ValueError as e:
        clients.remove(websocket)