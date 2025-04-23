from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
import uvicorn

app = FastAPI()

# 跨域允许
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# { group: { username: websocket } }
group_connections: Dict[str, Dict[str, WebSocket]] = {}
# { username: role }
user_roles: Dict[str, str] = {}

@app.websocket("/ws/{group}/{username}")
async def websocket_endpoint(websocket: WebSocket, group: str, username: str):
    await websocket.accept()

    if group not in group_connections:
        group_connections[group] = {}
    group_connections[group][username] = websocket
    print(f"[连接] {username} 加入分组 {group}")

    try:
        while True:
            data = await websocket.receive_text()

            if data.startswith("ROLE::"):
                # 存储角色
                role = data.split("::")[1]
                user_roles[username] = role
                print(f"[角色] {username} 的角色是 {role}")
                await broadcast_user_list(group)

            elif data.startswith("CALL::"):
                caller = data.split("::")[1]
                await broadcast_call(group, caller)

            elif data.startswith("KICK::"):
                target = data.split("::")[1]
                role = user_roles.get(username, "")
                if role != "admin":
                    print(f"[拒绝] 非管理员 {username} 尝试踢人")
                    continue
                await kick_user(group, target)

    except WebSocketDisconnect:
        print(f"[断开] {username} 离开分组 {group}")
        group_connections[group].pop(username, None)
        user_roles.pop(username, None)
        if not group_connections[group]:
            group_connections.pop(group)
        await broadcast_user_list(group)

# 向同组其他成员广播呼叫
async def broadcast_call(group: str, caller: str):
    if group not in group_connections:
        return
    for username, conn in group_connections[group].items():
        if username != caller:
            await conn.send_text(f"CALL::{caller}")
    print(f"[广播] {caller} 呼叫了分组 {group} 的成员")

# 广播在线用户列表
async def broadcast_user_list(group: str):
    if group not in group_connections:
        return
    user_list = ",".join(group_connections[group].keys())
    for conn in group_connections[group].values():
        await conn.send_text(f"USER_LIST::{user_list}")

# 踢出用户
async def kick_user(group: str, target: str):
    if group not in group_connections:
        return
    conn = group_connections[group].get(target)
    if conn:
        await conn.send_text("KICKED")
        await conn.close()
        group_connections[group].pop(target, None)
        user_roles.pop(target, None)
        await broadcast_user_list(group)
        print(f"[移除] {target} 被踢出分组 {group}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
