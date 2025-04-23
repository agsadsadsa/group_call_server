from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 用户连接映射
user_connections = {}  # {username: websocket}
user_groups = {}       # {username: set(groups)}
group_members = {}     # {group: set(usernames)}

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    user_connections[username] = websocket
    user_groups[username] = set()

    print(f"✅ 用户 {username} 已连接")

    try:
        while True:
            data = await websocket.receive_text()

            if data.startswith("JOIN_GROUP::"):
                _, group = data.split("::")
                user_groups[username].add(group)
                group_members.setdefault(group, set()).add(username)
                await websocket.send_text(f"JOINED::{group}")
                await notify_user_list(group)

            elif data.startswith("LEAVE_GROUP::"):
                _, group = data.split("::")
                user_groups[username].discard(group)
                group_members.get(group, set()).discard(username)
                await websocket.send_text(f"LEFT::{group}")
                await notify_user_list(group)

            elif data.startswith("GROUP_CALL::"):
                _, group = data.split("::")
                for member in group_members.get(group, []):
                    if member != username and member in user_connections:
                        await user_connections[member].send_text(f"GROUP_CALL::{username}::{group}")

            elif data.startswith("GET_USERS::"):
                _, group = data.split("::")
                users = ",".join(group_members.get(group, []))
                await websocket.send_text(f"USERS::{group}::{users}")

    except WebSocketDisconnect:
        print(f"❌ 用户 {username} 断开连接")
        if username in user_connections:
            del user_connections[username]
        for group in user_groups.get(username, []):
            group_members[group].discard(username)
            await notify_user_list(group)
        user_groups.pop(username, None)

async def notify_user_list(group):
    users = group_members.get(group, set())
    message = f"USERS::{group}::{','.join(users)}"
    for user in users:
        ws = user_connections.get(user)
        if ws:
            await ws.send_text(message)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
