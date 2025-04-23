from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

groups = {}  # { group_name: [WebSocket, ...] }
connections = {}  # { WebSocket: group_name }

@app.websocket("/ws/{group}/{user}")
async def websocket_endpoint(websocket: WebSocket, group: str, user: str):
    await websocket.accept()
    if group not in groups:
        groups[group] = []
    groups[group].append(websocket)
    connections[websocket] = group
    print(f"{user} joined group {group}")

    try:
        while True:
            data = await websocket.receive_text()
            if data.startswith("CALL:"):
                _, target_group, from_user = data.split(":")
                if target_group in groups:
                    for conn in groups[target_group]:
                        if conn != websocket:
                            await conn.send_text(f"CALL_FROM:{from_user}")
    except WebSocketDisconnect:
        print(f"{user} disconnected")
        groups[group].remove(websocket)
        del connections[websocket]

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000)
