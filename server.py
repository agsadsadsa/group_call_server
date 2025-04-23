import asyncio
import websockets
import json
from collections import defaultdict

# 数据结构：{ group_name: {username: websocket} }
groups = defaultdict(dict)

async def notify_users():
    """广播当前在线用户列表到每个连接的客户端"""
    for group, users in groups.items():
        msg = {
            "type": "USER_LIST",
            "group": group,
            "users": list(users.keys())
        }
        for ws in users.values():
            await safe_send(ws, json.dumps(msg))

async def safe_send(ws, msg):
    try:
        await ws.send(msg)
    except:
        pass  # 忽略发送失败的连接

async def handler(websocket, path):
    username = None
    joined_groups = set()

    try:
        async for message in websocket:
            data = json.loads(message)

            if data["type"] == "REGISTER":
                username = data["username"]
                initial_groups = data.get("groups", [])
                for g in initial_groups:
                    groups[g][username] = websocket
                    joined_groups.add(g)
                await notify_users()

            elif data["type"] == "JOIN_GROUP":
                group = data["group"]
                if username:
                    groups[group][username] = websocket
                    joined_groups.add(group)
                    await notify_users()

            elif data["type"] == "LEAVE_GROUP":
                group = data["group"]
                if username and group in groups and username in groups[group]:
                    del groups[group][username]
                    joined_groups.discard(group)
                    await notify_users()

            elif data["type"] == "GROUP_CALL":
                group = data["group"]
                sender = data["from"]
                for user, ws in groups.get(group, {}).items():
                    if user != sender:
                        await safe_send(ws, json.dumps({
                            "type": "GROUP_CALL",
                            "from": sender,
                            "group": group
                        }))

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # 清理用户连接
        for g in list(joined_groups):
            if username and username in groups[g]:
                del groups[g][username]
        await notify_users()

async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("✅ Server running on ws://0.0.0.0:8765")
        await asyncio.Future()  # 永远阻塞

if __name__ == "__main__":
    asyncio.run(main())
