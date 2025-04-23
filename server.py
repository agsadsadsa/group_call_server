# server.py
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

# group -> list of (WebSocket, username)
groups = {}
user_groups = {}  # websocket -> set of groups
usernames = {}  # websocket -> username

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    usernames[websocket] = username
    user_groups[websocket] = set()
    print(f"✅ 用户 {username} 已连接")

    try:
        while True:
            data = await websocket.receive_text()

            if data.startswith("JOIN:"):
                _, group = data.split(":")
                groups.setdefault(group, []).append((websocket, username))
                user_groups[websocket].add(group)
                print(f"➕ {username} 加入了分组 {group}")
                await send_user_list(group)

            elif data.startswith("LEAVE:"):
                _, group = data.split(":")
                if group in groups:
                    groups[group] = [(ws, u) for ws, u in groups[group] if ws != websocket]
                    user_groups[websocket].discard(group)
                    print(f"➖ {username} 离开了分组 {group}")
                    await send_user_list(group)

            elif data.startswith("CALL:"):
                _, target_group = data.split(":")
                if target_group in groups:
                    for conn, uname in groups[target_group]:
                        if conn != websocket:
                            await conn.send_text(f"CALL_FROM:{username}:{target_group}")

            elif data.startswith("LIST_USERS:"):
                _, group = data.split(":")
                await send_user_list(group, websocket)

            elif data == "LIST_GROUPS":
                group_list = list(user_groups[websocket])
                await websocket.send_text(f"GROUP_LIST:{','.join(group_list)}")

    except WebSocketDisconnect:
        print(f"❌ 用户 {username} 断开连接")
        for group in list(user_groups.get(websocket, [])):
            groups[group] = [(ws, u) for ws, u in groups[group] if ws != websocket]
            await send_user_list(group)
        user_groups.pop(websocket, None)
        usernames.pop(websocket, None)

async def send_user_list(group, ws=None):
    user_list = [u for ws_, u in groups.get(group, [])]
    msg = f"USER_LIST:{group}:{','.join(user_list)}"
    if ws:
        await ws.send_text(msg)
    else:
        for conn, _ in groups.get(group, []):
            await conn.send_text(msg)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
