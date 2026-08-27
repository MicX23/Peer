from fastapi import APIRouter, WebSocket, Request
import asyncio

router = APIRouter()

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    node = websocket.app.state.node
    events = websocket.app.state.events_core  # ← читаем отсюда

    await websocket.accept()
    try:
        while True:
            data = await events.get()
            await websocket.send_json(data)
    except asyncio.CancelledError:
        print('Остановка сервера') # Остановка сервера
    except WebSocketDisconnect:
        # Когда клиент отключился
        pass