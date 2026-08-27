import Node, signal, sys, asyncio, uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from electron_app .routes import ws, get, create #, system
from contextlib import asynccontextmanager




@asynccontextmanager
async def lifespan(app: FastAPI):
    events = asyncio.Queue(maxsize=300)
    node = Node.Node(events)
    await node.start()
    # await node.user_loaded.wait()     # ← если нужно ждать загрузку ДО старта сервера

    app.state.node = node             # передаём в роутеры
    app.state.events_core = events

    yield                             # сервер работает

    node.request_shutdown()           # uvicorn вызовет это при остановке


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    # app.include_router(system.router)
    app.include_router(ws.router)
    app.include_router(get.router)
    app.include_router(create.router)
    return app