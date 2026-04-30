import os
import base64
import tempfile
import asyncio
import json, io
import sys
import traceback



if len(sys.argv) > 1:
    DATA_ROOT = sys.argv[1]
else:
    # Если запустили просто python main.py, оставляем как было (текущая папка)
    DATA_ROOT = os.path.dirname(os.path.abspath(__file__))

# Создаем папку profiles, чтобы не засорять корень
PROFILES_DIR = os.path.join(DATA_ROOT, "profiles")
os.makedirs(PROFILES_DIR, exist_ok=True)

os.chdir(PROFILES_DIR)

from core.Node import Node

print(f"[Python Init] Рабочая директория изменена на: {os.getcwd()}")

def get_data_dir():
    """
    Получает директорию для хранения данных.
    Если передан аргумент из Electron, использует его.
    Иначе использует текущую папку (для отладки).
    """
    if len(sys.argv) > 1:
        # Первый аргумент - это путь к userData от Electron
        base_dir = sys.argv[1]
    else:
        # Фоллбэк, если запускаем Python напрямую без Electron
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Создаем подпапку для профилей внутри userData
    profiles_dir = os.path.join(base_dir, 'profiles')
    os.makedirs(profiles_dir, exist_ok=True)
    return profiles_dir

DATA_DIR = get_data_dir()
print(f"[Python] Data directory initialized at: {DATA_DIR}")

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class Bridge:
    def __init__(self):
        self.node = None
        # Храним активные задачи слушателей событий (events)
        self.active_event_listeners = {}
        # Храним активные задачи слушателей сообщений (messages)
        self.active_message_listeners = {}


    async def emit(self, data: dict):
        try:
            line = json.dumps(data, ensure_ascii=False) + "\n"
            sys.stdout.write(line)
            await asyncio.to_thread(sys.stdout.flush)
        except Exception as e:
            print(f"Emit error: {e}", file=sys.stderr)

    # --- Слушатель СОБЫТИЙ (подключения, файлы и т.д.) ---
    async def _start_space_events_listener(self, space_id: str):
        if space_id in self.active_event_listeners:
            return 
        task = asyncio.create_task(self._listen_space_events(space_id), name=f"evt_{space_id}")
        self.active_event_listeners[space_id] = task

    async def _listen_space_events(self, space_id: str):
        try:
            while True:
                if space_id not in self.node.spaces:
                    break
                space = self.node.spaces[space_id]
                try:
                    event = await asyncio.wait_for(space.events.get(), timeout=1.0)
                    
                    ui_event = {
                        "type": "system_event",
                        "space_id": space_id,
                        "timestamp": asyncio.get_event_loop().time()
                    }

                    if event['type'] in ['user_connected', 'user_joined']:
                        ui_event["text"] = f"{event['name']} подключился"
                        ui_event["isSystem"] = True
                    elif event['type'] == 'user_disconnected':
                        ui_event["text"] = f"{event['name']} отключился"
                        ui_event["isSystem"] = True
                    elif event['type'] == 'file_received':
                        # Специальный тип для файлов, чтобы отобразить их красиво
                        ui_event["type"] = "new_file_message"
                        
                        # === ИСПРАВЛЕНИЕ ЗДЕСЬ ===
                        # Определяем автора по sender_id
                        sender_id = event.get('sender_id')
                        author_name = "Unknown"
                        is_me = False

                        if self.node.User and sender_id:
                            my_verify_key_hex = self.node.User.verify_key.encode().hex()
                            if sender_id == my_verify_key_hex:
                                is_me = True
                                author_name = self.node.User.profile.get("name", "Me")
                            else:
                                # Ищем имя пользователя в списке пользователей пространства
                                user_data = space.users.get(sender_id)
                                if user_data and 'name' in user_data:
                                    author_name = user_data['name']
                                else:
                                    author_name = "Unknown"

                        ui_event["author"] = author_name
                        ui_event["fileName"] = event.get('file_name', 'unknown.dat')
                        ui_event["fileSize"] = event.get('size', 0)
                        ui_event["tag"] = event.get('tag', '')
                        ui_event["isMe"] = is_me
                        ui_event["filePath"] = event.get('path', '')
                    else:
                        ui_event["text"] = f"Событие: {event['type']}"
                        ui_event["isSystem"] = True

                    await self.emit(ui_event)

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    # print(f"Listener error for {space_id}: {e}", file=sys.stderr)
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if space_id in self.active_event_listeners:
                del self.active_event_listeners[space_id]

    async def _start_space_messages_listener(self, space_id: str):
        if space_id in self.active_message_listeners:
            return
        task = asyncio.create_task(self._listen_space_messages(space_id), name=f"msg_{space_id}")
        self.active_message_listeners[space_id] = task

    async def _listen_space_messages(self, space_id: str):
        try:
            while True:
                if space_id not in self.node.spaces:
                    break
                space = self.node.spaces[space_id]
                try:
                    # Ждем сообщение из очереди сообщений пространства
                    sender_id, message_text = await asyncio.wait_for(space.messages.get(), timeout=1.0)
                    
                    # Определяем, мое ли это сообщение
                    # Если мы есть в пространстве, сравниваем наш ID с ID отправителя
                    is_me = False
                    if self.node.User:
                        my_verify_key_hex = self.node.User.verify_key.encode().hex()
                        if sender_id == my_verify_key_hex:
                            is_me = True
                            # Если это я, берем имя из своего профиля
                            author_name = self.node.User.profile.get("name", "Me")
                        else:
                            # Если это кто-то другой, ищем его имя в списке пользователей пространства
                            # space.users имеет структуру: { verify_key_hex: { 'name': ..., 'addr': ... } }
                            user_data = space.users.get(sender_id)
                            if user_data and 'name' in user_data:
                                author_name = user_data['name']
                            else:
                                # Если пользователь есть в списке, но без имени (редкий кейс), или его нет в списке
                                author_name = "Unknown" 

                    # Отправляем в React
                    await self.emit({
                        "type": "new_message",
                        "space_id": space_id,
                        "author": author_name, # Можно подтянуть имя по ID, если нужно
                        "text": message_text,
                        "isMe": is_me,
                        "timestamp": asyncio.get_event_loop().time()
                    })

                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    # print(f"Message listener error for {space_id}: {e}", file=sys.stderr)
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if space_id in self.active_message_listeners:
                del self.active_message_listeners[space_id]


    async def handle_command(self, cmd: dict):
        cmd_type = cmd.get("type")

        if cmd_type == "init":
            if not self.node:
                try:
                    self.node = Node()
                    asyncio.create_task(self.node.start(), name="node_main")
                    
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
            else:
                await self.emit({"type": "node_ready"})
            return

        if not self.node:
            await self.emit({"type": "error", "message": "Node not initialized"})
            return
        await self.node._ss_register_all()
        try:
            if cmd_type == "create_user":
                name = cmd.get("name", "User")
                success = self.node.create_user(name=name)
                if success:
                    await self.emit({"type": "user_created", "name": name})
                else:
                    await self.emit({"type": "error", "message": "Failed to create user"})

            elif cmd_type == "list_spaces":
                spaces = []
                for sp_id, sp_obj in self.node.spaces.items():
                    spaces.append({
                        "id": sp_id,
                        "name": sp_obj.name,
                        "addr": sp_obj.addr
                    })
                await self.emit({"type": "spaces_list", "data": spaces})

            elif cmd_type == "create_space":
                if self.node.User is None:
                    await self.emit({"type": "error", "message": "Login required"})
                    return
                name = cmd.get("name", "NewSpace")
                space_obj = await self.node.space_add(name)
                if space_obj:
                    await self.emit({"type": "space_created", "id": space_obj.space_id})
                    
                    # Запускаем слушатели для нового пространства
                    await self._start_space_events_listener(space_obj.space_id)
                    await self._start_space_messages_listener(space_obj.space_id)
                    
                    await self.handle_command({"type": "list_spaces"})
                else:
                    await self.emit({"type": "error", "message": "Failed to create space"})

            elif cmd_type == "connect_space":
                if self.node.User is None:
                    await self.emit({"type": "error", "message": "Login required"})
                    return
                space_id = cmd.get("id")
                if not space_id:
                    await self.emit({"type": "error", "message": "Space ID required"})
                    return
                
                success = await self.node.connect_to_space(space_id)
                if success:
                    await self.emit({"type": "space_connected", "id": space_id})
                    
                    # ВАЖНО: Подключение асинхронное. Пространство появится в списке не мгновенно.
                    # Делаем небольшую паузу, чтобы демоны Node успели обработать ответ от сервера
                    # и добавить пространство в self.node.spaces
                    await asyncio.sleep(0.5) 
                    
                    await self.handle_command({"type": "list_spaces"})
                    
                    # Запускаем слушатели (если пространство успешно добавилась)
                    if space_id in self.node.spaces:
                        await self._start_space_events_listener(space_id)
                        await self._start_space_messages_listener(space_id)
                    else:
                        # Если пространство все еще не в списке, возможно стоит попробовать еще раз позже
                        # или вывести ошибку, но пока оставим так
                        print(f"Warning: Space {space_id} connected but not found in local list immediately")

                else:
                    await self.emit({"type": "error", "message": "Connection failed"})

            elif cmd_type == "delete_space":
                if self.node.User is None:
                    await self.emit({"type": "error", "message": "Login required"})
                    return
                space_id = cmd.get("id")
                if not space_id:
                    await self.emit({"type": "error", "message": "Space ID required"})
                    return
                
                # Останавливаем слушатели
                if space_id in self.active_event_listeners:
                    self.active_event_listeners[space_id].cancel()
                if space_id in self.active_message_listeners:
                    self.active_message_listeners[space_id].cancel()
                
                success = await self.node.space_del(space_id)
                if success:
                    await self.emit({"type": "space_deleted", "id": space_id})
                    await self.handle_command({"type": "list_spaces"})
                else:
                    await self.emit({"type": "error", "message": "Delete failed"})

            elif cmd_type == "send_message":
                space_id = cmd.get("space_id")
                message_text = cmd.get("message")
                if not space_id or not message_text:
                    await self.emit({"type": "error", "message": "Missing data"})
                    return
                
                if space_id in self.node.spaces:
                    res = await self.node.spaces[space_id].send_message(message_text)
                    if not res:
                        await self.emit({"type": "error", "message": "Send failed"})
                else:
                    await self.emit({"type": "error", "message": "Space not found"})

            elif cmd_type == "send_file":
                space_id = cmd.get("space_id")
                file_name = cmd.get("fileName")
                file_data_b64 = cmd.get("data") 
                tag = cmd.get("tag", "default")
                
                if not space_id or not file_data_b64:
                    await self.emit({"type": "error", "message": "Missing file data"})
                    return
                
                if space_id not in self.node.spaces:
                    await self.emit({"type": "error", "message": "Space not found"})
                    return

                try:
                    file_bytes = base64.b64decode(file_data_b64)
                    
                    temp_dir = os.path.join(os.getcwd(), "temp_files")
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir)
                    
                    safe_path = os.path.join(temp_dir, file_name)
                    with open(safe_path, 'wb') as f:
                        f.write(file_bytes)
                    
                    space_obj = self.node.spaces[space_id]
                    asyncio.create_task(space_obj.send_file(safe_path, tag=tag))
                    
                    await self.emit({
                        "type": "new_file_message",
                        "space_id": space_id,
                        "author": self.node.User.profile.get("name", "Me"),
                        "fileName": file_name,
                        "fileSize": len(file_bytes),
                        "tag": tag,
                        "isMe": True
                    })

                except Exception as e:
                    await self.emit({"type": "error", "message": f"File send error: {str(e)}"})
                    traceback.print_exc()

            else:
                await self.emit({"type": "error", "message": f"Unknown command: {cmd_type}"})

        except Exception as e:
            await self.emit({"type": "error", "message": str(e)})
            traceback.print_exc()

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