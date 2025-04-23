from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 分组结构: {group: [(websocket, username)]}
groups = {}
connections = {}

@app.websocket("/ws/{group}/{user}")
async def websocket_endpoint(websocket: WebSocket, group: str, user: str):
    await websocket.accept()

    if group not in groups:
        groups[group] = []
    groups[group].append((websocket, user))
    connections[websocket] = group

    print(f"✅ 用户 {user} 加入了分组 {group}")

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("CALL:"):
                _, target_group, from_user = data.split(":")
                print(f"📣 呼叫请求：{from_user} 呼叫分组 {target_group}")
                if target_group in groups:
                    for conn, _ in groups[target_group]:
                        if conn != websocket:
                            await conn.send_text(f"CALL_FROM:{from_user}")

            elif data.startswith("LIST_USERS:"):
                _, group_name = data.split(":")
                if group_name in groups:
                    user_list = [u for _, u in groups[group_name]]
                    await websocket.send_text(f"USER_LIST:{','.join(user_list)}")

    except WebSocketDisconnect:
        print(f"❌ 用户 {user} 断开连接")
        if group in groups:
            groups[group] = [(ws, u) for ws, u in groups[group] if ws != websocket]
        del connections[websocket]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
