import asyncio, json, httpx
from websockets.asyncio.client import connect

async def listener(ws,user):
    async for message in ws:
        print(message)
        ms = json.loads(message)
        match ms['type']:
            case 'user_not_loaded':pass

    
async def create_user(client, user, loop):
    resp = await client.get("/get/user")
    if resp.status_code//100 == 2:
        user = resp.json()['name']
        return
    if resp.status_code//100 == 3:
        print("Ошибка доступа")
        return
    u_name = await loop.run_in_executor(None, input, 'name? :: ')
    resp = await client.post("/create/user", json={"name": u_name})
    data = resp.json()
    if data.get("status") == 'ok': return data['name']
    else: print(f'Ошибка?\ndata: [{data}]')

async def get_user(user):
    print(user)

async def main():
    ws = await connect("ws://127.0.0.1:21212/ws")
    client = httpx.AsyncClient(base_url="http://127.0.0.1:21212")

    loop = asyncio.get_running_loop()
    user = None

    tasks = [
        asyncio.create_task(listener(ws, user), name='listener'),
    ]

    while True:
        data = await loop.run_in_executor(None, input, ':: ')
        match data:
            case '\\q': break
            case '\\user': 
                if user:
                    await get_user(user) 
                else: user = await create_user(client,user,loop)

    for task in tasks:
        task.cancel()

    await ws.close()
    

asyncio.run(main())