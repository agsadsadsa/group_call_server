from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储连接分组信息
groups = {}
connections = {}

@app.websocket("/ws/{group}/{user}")
async def websocket_endpoint(websocket: WebSocket, group: str, user: str):
    await websocket.accept()

    if group not in groups:
        groups[group] = []
    groups[group].append(websocket)
    connections[websocket] = group

    print(f"✅ 用户 {user} 加入了分组 {group}")

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("CALL:"):
                _, target_group, from_user = data.split(":")
                print(f"📣 呼叫请求：{from_user} 呼叫分组 {target_group}")
                if target_group in groups:
                    for conn in groups[target_group]:
                        if conn != websocket:
                            await conn.send_text(f"CALL_FROM:{from_user}")
    except WebSocketDisconnect:
        print(f"❌ 用户 {user} 断开连接")
        groups[group].remove(websocket)
        del connections[websocket]

# Render 用 $PORT 启动服务
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
