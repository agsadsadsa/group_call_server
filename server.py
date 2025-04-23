# server.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# groups: { group_name: [(websocket, username)] }
groups = {}

@app.websocket("/ws/{group}/{username}")
async def websocket_endpoint(websocket: WebSocket, group: str, username: str):
    await websocket.accept()

    if group not in groups:
        groups[group] = []
    groups[group].append((websocket, username))
    print(f"✅ {username} joined group {group}")

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("CALL:"):
                _, target_group, from_user = data.split(":")
                if target_group in groups:
                    for conn, user in groups[target_group]:
                        if conn != websocket:
                            await conn.send_text(f"CALL_FROM:{from_user}")
            elif data.startswith("LIST_USERS:"):
                _, target_group = data.split(":")
                if target_group in groups:
                    user_list = [user for _, user in groups[target_group]]
                    await websocket.send_text(f"USER_LIST:{','.join(user_list)}")

    except WebSocketDisconnect:
        print(f"❌ {username} disconnected from group {group}")
        if group in groups:
            groups[group] = [(ws, u) for ws, u in groups[group] if ws != websocket]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
