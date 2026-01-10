from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from datetime import datetime
import uvicorn

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.rooms = {}        # websocket -> room
        self.users = {}        # websocket -> username

    def now(self):
        return datetime.now().isoformat()

    async def connect(self, ws: WebSocket, username: str, room: str):
        self.rooms[ws] = room
        self.users[ws] = username
        await self.broadcast_users(room)
        await self.broadcast(room, {
            "type": "system",
            "message": f"{username} joined the room 👋",
            "timestamp": self.now()
        })

    def disconnect(self, ws: WebSocket):
        room = self.rooms.get(ws)
        username = self.users.get(ws)
        self.rooms.pop(ws, None)
        self.users.pop(ws, None)
        return username, room

    async def broadcast(self, room: str, data: dict):
        for ws, ws_room in self.rooms.items():
            if ws_room == room:
                await ws.send_json(data)

    async def broadcast_users(self, room: str):
        users = [
            name for ws, name in self.users.items()
            if self.rooms.get(ws) == room
        ]
        await self.broadcast(room, {
            "type": "users",
            "users": users
        })

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()

    try:
        join = await ws.receive_json()
        username = join["username"]
        room = join["room"]

        await manager.connect(ws, username, room)

        while True:
            data = await ws.receive_json()

            if data["type"] == "chat":
                await manager.broadcast(room, {
                    "type": "chat",
                    "username": username,
                    "message": data["message"],
                    "timestamp": manager.now()
                })

            elif data["type"] == "typing":
                await manager.broadcast(room, {
                    "type": "typing",
                    "username": username
                })

            elif data["type"] == "stop_typing":
                await manager.broadcast(room, {
                    "type": "stop_typing"
                })

            elif data["type"] == "switch_room":
                new_room = data["room"]
                old_room = manager.rooms.get(ws)

                if new_room == old_room:
                    continue

                manager.rooms[ws] = new_room

                await manager.broadcast_users(old_room)
                await manager.broadcast(old_room, {
                    "type": "system",
                    "message": f"{username} left the room ❌",
                    "timestamp": manager.now()
                })

                await manager.broadcast_users(new_room)
                await manager.broadcast(new_room, {
                    "type": "system",
                    "message": f"{username} joined the room 👋",
                    "timestamp": manager.now()
                })

                room = new_room

    except WebSocketDisconnect:
        username, room = manager.disconnect(ws)
        if room:
            await manager.broadcast_users(room)
            await manager.broadcast(room, {
                "type": "system",
                "message": f"{username} left the room ❌",
                "timestamp": manager.now()
            })

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
