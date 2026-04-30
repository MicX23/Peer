import sys
import os
import asyncio
import json
import traceback

# Добавляем путь к корню проекта, чтобы импортировать core и User
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.Node import Node
except ImportError as e:
    print(f"CRITICAL: Cannot import Node. {e}", file=sys.stderr)
    sys.exit(1)

class Bridge:
    def __init__(self):
        self.node = None

    async def emit(self, data: dict):
        """Отправляет JSON в stdout для Electron"""
        try:
            line = json.dumps(data, ensure_ascii=False) + "\n"
            sys.stdout.write(line)
            await asyncio.to_thread(sys.stdout.flush)
        except Exception as e:
            print(f"Emit error: {e}", file=sys.stderr)


    async def _start_message_listener(self):
        """Фоновая задача для прослушивания сообщений из очередей пространств"""
        while True:
            try:
                # Небольшая задержка, чтобы не грузить CPU вхолостую
                await asyncio.sleep(0.1)
                
                if not self.node or not self.node.spaces:
                    continue

                # Проходим по всем активным пространствам
                for space_id, space_obj in self.node.spaces.items():
                    # Проверяем, есть ли сообщения в очереди (не блокируя поток)
                    # В твоем TUI используется await space.messages.get(), но здесь нам нужно 
                    # проверить наличие без блокировки, или использовать get_nowait() если очередь asyncio.Queue
                    
                    # Предполагаем, что space.messages - это asyncio.Queue
                    while not space_obj.messages.empty():
                        try:
                            user_id, message = space_obj.messages.get_nowait()
                            
                            # Получаем имя отправителя из пользователей пространства
                            sender_name = "Unknown"
                            sender_addr = ""
                            if user_id in space_obj.users:
                                sender_name = space_obj.users[user_id].get('name', 'Unknown')
                                sender_addr = space_obj.users[user_id].get('addr', '')

                            # Отправляем событие в React
                            await self.emit({
                                "type": "new_message",
                                "space_id": space_id,
                                "author": sender_name,
                                "text": message,
                                "timestamp": asyncio.get_event_loop().time() # Или используй time.time()
                            })
                        except asyncio.QueueEmpty:
                            break
                        except Exception as e:
                            print(f"Error processing message in space {space_id}: {e}", file=sys.stderr)
                            
            except Exception as e:
                print(f"Listener error: {e}", file=sys.stderr)
                await asyncio.sleep(1)

    async def handle_command(self, cmd: dict):
        cmd_type = cmd.get("type")

        # 1. Инициализация Node
        if cmd_type == "init":
            if not self.node:
                try:
                    self.node = Node()
                    # Запускаем основной цикл Node в фоне
                    asyncio.create_task(self.node.start(), name="node_main")
                    
                    asyncio.create_task(self._start_message_listener(), name="msg_listener")
                    # Проверяем, есть ли пользователь
                    if self.node.User is None:
                        await self.emit({"type": "need_profile_setup"})
                    else:
                        await self.emit({
                            "type": "user_loaded", 
                            "name": self.node.User.profile.get("name", "User")
                        })
                    
                    await self.emit({"type": "node_ready"})
                except Exception as e:
                    await self.emit({"type": "error", "message": f"Node init failed: {str(e)}"})
                    traceback.print_exc()
            elif cmd_type == "send_message":
                space_id = cmd.get("space_id")
                message_text = cmd.get("message")
                
                if not self.node.User:
                    await self.emit({"type": "error", "message": "Login required"})
                    return

                if not space_id or not message_text:
                    await self.emit({"type": "error", "message": "Missing space_id or message"})
                    return
                
                if space_id not in self.node.spaces:
                    await self.emit({"type": "error", "message": "Space not found or not connected"})
                    return

                try:
                    # Вызываем метод отправки из объекта пространства
                    res = await self.node.spaces[space_id].send_message(message_text)
                    if not res:
                        await self.emit({"type": "error", "message": "Failed to send message"})
                except Exception as e:
                    await self.emit({"type": "error", "message": str(e)})
                else:
                    await self.emit({"type": "node_ready"})
                return

            if not self.node:
                await self.emit({"type": "error", "message": "Node not initialized"})
                return

        # 2. Создание пользователя
        if cmd_type == "create_user":
            name = cmd.get("name", "User")
            try:
                # В Node.py create_user скорее всего синхронный
                success = self.node.create_user(name=name)
                if success:
                    await self.emit({
                        "type": "user_created", 
                        "name": name
                    })
                    await self.node._ss_register_all()
                else:
                    await self.emit({"type": "error", "message": "Failed to create user"})
            except Exception as e:
                await self.emit({"type": "error", "message": str(e)})

        # 3. Получение списка пространств
        elif cmd_type == "list_spaces":
            try:
                spaces = []
                for sp_id, sp_obj in self.node.spaces.items():
                    spaces.append({
                        "id": sp_id,
                        "name": sp_obj.name,
                        "addr": sp_obj.addr
                    })
                await self.emit({"type": "spaces_list", "data": spaces})
            except Exception as e:
                await self.emit({"type": "error", "message": str(e)})

        # 4. Создание пространства
        elif cmd_type == "create_space":
            if self.node.User is None:
                await self.emit({"type": "error", "message": "Login required"})
                return
            await self.node._ss_register_all()
            name = cmd.get("name", "NewSpace")
            try:
                await self.node.space_add(name)
                await self.emit({"type": "space_created", "name": name})
                # Сразу обновляем список
                await self.handle_command({"type": "list_spaces"})
            except Exception as e:
                await self.emit({"type": "error", "message": str(e)})

        # 5. Отправка сообщения
        elif cmd_type == "send_message":
            space_id = cmd.get("space_id")
            message = cmd.get("message")
            if not space_id or not message:
                await self.emit({"type": "error", "message": "Missing space_id or message"})
                return
            
            try:
                if space_id in self.node.spaces:
                    await self.node.spaces[space_id].send_message(message)
                else:
                    await self.emit({"type": "error", "message": "Space not found"})
            except Exception as e:
                await self.emit({"type": "error", "message": str(e)})
        elif cmd_type == "connect_space":
            if self.node.User is None:
                await self.emit({"type": "error", "message": "Login required"})
                return
            space_id = cmd.get("id")
            if not space_id:
                await self.emit({"type": "error", "message": "Space ID required"})
                return
            
            try:
                # Вызываем метод подключения из Node (как в TUI: await node.connect_to_space(id))
                await self.node.connect_to_space(space_id)
                await self.emit({"type": "space_connected", "id": space_id})
                # После успешного подключения обновляем список пространств
                await self.handle_command({"type": "list_spaces"})
            except Exception as e:
                await self.emit({"type": "error", "message": f"Connect failed: {str(e)}"})

        elif cmd_type == "delete_space":
            if self.node.User is None:
                await self.emit({"type": "error", "message": "Login required"})
                return
            space_id = cmd.get("id")
            if not space_id:
                await self.emit({"type": "error", "message": "Space ID required"})
                return
            
            try:
                # Вызываем метод удаления (как в TUI: node.space_del(id))
                # В TUI это синхронный вызов, но если в Node он асинхронный - добавь await
                self.node.space_del(space_id)
                await self.emit({"type": "space_deleted", "id": space_id})
                # Обновляем список, чтобы пространство исчезло из UI
                await self.handle_command({"type": "list_spaces"})
            except Exception as e:
                await self.emit({"type": "error", "message": f"Delete failed: {str(e)}"})

        else:
            await self.emit({"type": "error", "message": f"Unknown command: {cmd_type}"})

async def read_stdin():
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        yield line.strip()

async def main():
    bridge = Bridge()
    async for line in read_stdin():
        if not line: continue
        try:
            cmd = json.loads(line)
            await bridge.handle_command(cmd)
        except json.JSONDecodeError:
            await bridge.emit({"type": "error", "message": "Invalid JSON"})
        except Exception as e:
            await bridge.emit({"type": "error", "message": str(e)})

if __name__ == "__main__":
    asyncio.run(main())