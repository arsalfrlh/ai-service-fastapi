from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from collections import defaultdict
import json

app = FastAPI()


class ConnectionManager:
    def __init__(self):
        # Menyimpan semua websocket
        self.connections: list[WebSocket] = []

        # Menyimpan room -> list websocket
        self.rooms: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)

        # Hapus websocket dari semua room
        for room in self.rooms.values():
            if websocket in room:
                room.remove(websocket)

    def subscribe(self, websocket: WebSocket, room: str):
        if websocket not in self.rooms[room]:
            self.rooms[room].append(websocket)

    def unsubscribe(self, websocket: WebSocket, room: str):
        if room in self.rooms:
            if websocket in self.rooms[room]:
                self.rooms[room].remove(websocket)

            if len(self.rooms[room]) == 0:
                del self.rooms[room]

    async def send(self, websocket: WebSocket, data: dict):
        await websocket.send_json(data)

    async def broadcast(self, room: str, data: dict):
        if room not in self.rooms:
            return

        disconnected = []

        for websocket in self.rooms[room]:
            try:
                await websocket.send_json(data)
            except:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(websocket)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):

    await manager.connect(websocket)

    await manager.send(websocket, {
        "event": "connected",
        "message": "WebSocket Connected"
    })

    try:

        while True:

            data = await websocket.receive_json()

            action = data.get("action")

            # ==========================
            # Subscribe
            # ==========================
            if action == "subscribe":

                room = data.get("room")

                manager.subscribe(websocket, room)

                await manager.send(websocket, {
                    "event": "subscribe",
                    "room": room,
                    "message": f"Joined room {room}"
                })

            # ==========================
            # Unsubscribe
            # ==========================
            elif action == "unsubscribe":

                room = data.get("room")

                manager.unsubscribe(websocket, room)

                await manager.send(websocket, {
                    "event": "unsubscribe",
                    "room": room,
                    "message": f"Left room {room}"
                })

            # ==========================
            # Broadcast
            # ==========================
            elif action == "broadcast":

                room = data.get("room")

                message = data.get("message")

                await manager.broadcast(room, {
                    "event": "message",
                    "room": room,
                    "message": message
                })

            # ==========================
            # Client -> Server
            # ==========================
            elif action == "echo":

                await manager.send(websocket, {
                    "event": "echo",
                    "data": data
                })

            else:

                await manager.send(websocket, {
                    "event": "error",
                    "message": "Unknown action"
                })

    except WebSocketDisconnect:

        manager.disconnect(websocket)

        print("Client disconnected")

# subscribe room dari kedua client
# {
#     "action": "subscribe",
#     "room": "room-1"
# }

# kirim broadcast ke client lain
# {
#     "action": "broadcast",
#     "room": "room-1",
#     "message": "Halo semuanya"
# }

# kirim data dari client ke server
# {
#     "action": "echo",
#     "nama": "Arsal",
#     "umur": 22
# }

# unsubscribe room
# {
#     "action": "unsubscribe",
#     "room": "room-1"
# }