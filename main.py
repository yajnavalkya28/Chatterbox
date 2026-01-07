from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()

# ---------- HTTP ROOT (Health Check) ----------
@app.get("/")
async def root():
    return {
        "message": "Server is running – Milestone 3"
    }

# ---------- CONNECTION MANAGER ----------
class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}
        self.users: dict[WebSocket, str] = {}
        self.user_room: dict[WebSocket, str] = {}

    async def join_room(self, websocket: WebSocket, username: str, room: str):
        if room not in self.rooms:
            self.rooms[room] = []

        self.rooms[room].append(websocket)
        self.users[websocket] = username
        self.user_room[websocket] = room

        await self.broadcast(room, {
            "type": "system",
            "message": f"{username} joined {room} 🟢"
        })

    async def leave_room(self, websocket: WebSocket):
        room = self.user_room.get(websocket)
        username = self.users.get(websocket, "Someone")

        if room and websocket in self.rooms.get(room, []):
            self.rooms[room].remove(websocket)
            await self.broadcast(room, {
                "type": "system",
                "message": f"{username} left {room} ❌"
            })

        self.users.pop(websocket, None)
        self.user_room.pop(websocket, None)

    async def broadcast(self, room: str, data: dict):
        for ws in self.rooms.get(room, []):
            await ws.send_json(data)

manager = ConnectionManager()

# ---------- WEBSOCKET ----------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            event = data.get("type")

            if event == "join":
                await manager.join_room(
                    websocket,
                    data.get("username", "Anonymous"),
                    data.get("room", "general")
                )

            elif event == "leave":
                await manager.leave_room(websocket)

            elif event == "chat":
                room = manager.user_room.get(websocket)
                if room:
                    await manager.broadcast(room, {
                        "type": "chat",
                        "username": manager.users.get(websocket),
                        "message": data.get("message")
                    })

            elif event == "typing":
                room = manager.user_room.get(websocket)
                if room:
                    await manager.broadcast(room, {
                        "type": "typing",
                        "username": manager.users.get(websocket)
                    })

            elif event == "stop_typing":
                room = manager.user_room.get(websocket)
                if room:
                    await manager.broadcast(room, {
                        "type": "stop_typing",
                        "username": manager.users.get(websocket)
                    })

    except WebSocketDisconnect:
        await manager.leave_room(websocket)

# ---------- RUN SERVER ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
