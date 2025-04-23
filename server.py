from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import Dict, List, Set
from collections import defaultdict
import uvicorn

app = FastAPI()

# 所有在线连接：{username: websocket}
active_connections: Dict[str, WebSocket] = {}

# 用户所属的分组：{username: set(group1, group2, ...)}
user_groups: Dict[str, Set[str]] = defaultdict(set)

# 每个分组的成员：{group: set(username1, username2, ...)}
group_members: Dict[str, Set[str]] = defaultdict(set)

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    active_connections[username] = websocket
    print(f"✅ 用户连接: {username}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[{username}] 收到: {data}")

            if data.startswith("JOIN_GROUP::"):
                _, group = data.split("::", 1)
                user_groups[username].add(group)
                group_members[group].add(username)
                await notify_user_list(group)

            elif data.startswith("LEAVE_GROUP::"):
                _, group = data.split("::", 1)
                user_groups[username].discard(group)
                group_members[group].discard(username)
                await notify_user_list(group)

            elif data.startswith("GROUP_CALL::"):
                _, group = data.split("::", 1)
                await broadcast_group_call(group, username)

            elif data == "GET_MY_GROUPS":
                groups = list(user_groups[username])
                await websocket.send_text("MY_GROUPS::" + "::".join(groups))

            elif data.startswith("GET_USERS::"):
                _, group = data.split("::", 1)
                await notify_user_list(group)

    except WebSocketDisconnect:
        print(f"❌ 用户断开: {username}")
        await handle_disconnect(username)

async def broadcast_group_call(group: str, caller: str):
    users = group_members.get(group, set())
    for user in users:
        if user != caller and user in active_connections:
            try:
                await active_connections[user].send_text(f"GROUP_CALL::{group}::{caller}")
            except:
                pass

async def notify_user_list(group: str):
    users = list(group_members[group])
    msg = "USER_LIST::" + ",".join(users)
    for user in group_members[group]:
        if user in active_connections:
            try:
                await active_connections[user].send_text(msg)
            except:
                pass

async def handle_disconnect(username: str):
    # 移除所有记录
    active_connections.pop(username, None)
    for group in list(user_groups[username]):
        group_members[group].discard(username)
        await notify_user_list(group)
    user_groups.pop(username, None)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
