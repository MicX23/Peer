import asyncio
import sys
import traceback
from core.Node import Node

# Глобальное хранилище для текущей активной задачи вывода сообщений
current_display_task = None

import asyncio
import sys
import traceback
from core.Node import Node

async def input_loop(node: Node):
    print("\n=== P2P Chat TUI (minimal) ===")
    print("Доступные команды:")
    print("  /unew <name>")
    print("  /logout")
    print("  /exit")
    print("================================\n")
    sys.stdout.flush()

    active_space_id = None  # ID пространства, в котором мы сейчас "находимся"
    current_display_task = None # Задача вывода сообщений для активного пространства
    async def space_message_displayer(space_id: str):
        """
        Задача, которая читает сообщения из конкретного пространства и выводит их.
        """
        try:
            while not node._shutdown.is_set():
                if space_id not in node.spaces:
                    break # Пространство удалено
                
                space = node.spaces[space_id]
                # Ждем сообщение. Если пространство закроется, может возникнуть ошибка
                try:
                    user_id, message = await asyncio.wait_for(space.messages.get(), timeout=1.0)
                    
                    # Проверка, актуально ли еще это пространство для вывода
                    # Сравниваем с замыканием active_space_id, но т.к. оно может измениться,
                    # лучше проверять наличие задачи в глобальном состоянии или просто печатать,
                    # если задача не отменена.
                    # Но так как мы отменяем старую задачу при переключении, то эта проверка безопасна.
                    
                    user_info = space.users.get(user_id)
                    if user_info:
                        name = user_info['name']
                        addr = user_info['addr']
                        # \r возвращает курсор в начало строки, чтобы не ломать ввод
                        print(f"\r[{space.name}] {name} ({addr}): {message}")
                    else:
                        print(f"\r[{space.name}] Unknown User: {message}")
                    
                    # Возвращаем приглашение ввода
                    prefix = f"{active_space_id[:8]}" if active_space_id else "NO SPACE"
                    print(f"[{prefix}]> ", end='', flush=True)
                    
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"\nОшибка в дисплее сообщений: {e}")

    async def space_event_displayer(space_id: str):
        """Выводит системные события (подключения/отключения)"""
        try:
            while not node._shutdown.is_set():
                if space_id not in node.spaces:
                    break
                
                space = node.spaces[space_id]
                try:
                    event = await asyncio.wait_for(space.events.get(), timeout=1.0)
                    
                    if active_space_id != space_id:
                        continue 

                    # Форматируем событие
                    if event['type'] == 'user_connected' or event['type'] == 'user_joined':
                        msg = f"Пользователь {event['name']} подключился"
                    elif event['type'] == 'user_disconnected':
                        msg = f"Пользователь {event['name']} отключился"
                    elif event['type'] == 'file_received':
                        size_kb = event['size'] / 1024
                        # Относительный путь для красоты, если он начинается с ./
                        display_path = event['path']
                        if display_path.startswith('./'):
                            display_path = display_path[2:]
                            
                        msg = f"Файл: {event['file_name']} ({size_kb:.1f} KB)"
                        msg += f"\n    Папка: {display_path}"
                    else:
                        msg = f"Событие: {event['type']}"

                    print(f"\r[{space.name}] SYSTEM: {msg}")
                    
                    # Возвращаем приглашение ввода
                    prefix = f"{active_space_id[:8]}" if active_space_id else "NO SPACE"
                    print(f"[{prefix}]> ", end='', flush=True)

                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"\nОшибка в дисплее событий: {e}")

    async def switch_space(new_space_id: str):
        nonlocal active_space_id, current_display_task
        
        # Отменяем предыдущую задачу вывода, если она была
        if current_display_task and not current_display_task.done():
            current_display_task.cancel()
            try:
                await current_display_task
            except asyncio.CancelledError:
                pass

        active_space_id = new_space_id
        if new_space_id and new_space_id in node.spaces:
            # Запускаем новую задачу для нового пространства
            current_display_task = asyncio.create_task(
                space_message_displayer(new_space_id), 
                name=f'display_{new_space_id[:8]}'
            )
            current_event_task = asyncio.create_task(
                space_event_displayer(new_space_id), 
                name=f'display_evt_{new_space_id[:8]}'
            )
            print(f"Переключено на пространство: {node.spaces[new_space_id].name}")
        else:
            active_space_id = None
            current_display_task = None
            print("Нет активного пространства для отображения")

    while not node._shutdown.is_set():
        try:
            # Формируем префикс
            prefix = f"{active_space_id[:8]}" if active_space_id else "NO SPACE"
            print(f"[{prefix}]> ", end='', flush=True)
            
            line = await asyncio.to_thread(input)
            line = line.strip()
            
            if not line:
                continue
            
            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()
            
            match cmd:
                case '/unew':
                    if node.User is not None:
                        print("Сначала выполните /logout")
                        continue
                    if len(parts) < 2:
                        print("Использование: /unew <имя>")
                        continue
                    name = parts[1]
                    if node.create_user(name=name):
                        print(f"Пользователь '{name}' создан")
                        print(f"verify_key: {node.User.verify_key.encode().hex()[:32]}...")
                    else:
                        print("Ошибка создания пользователя")

                case '/sendfile':
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    
                    if not active_space_id or active_space_id not in node.spaces:
                        print("Ошибка: Не выбрано активное пространство.")
                        continue
                    
                    # Ожидаемый формат: /sendfile <метка> <путь_к_файлу>
                    # Или: /sendfile <путь_к_файлу> (тогда метка будет 'default')
                    
                    args = parts[1].split() if len(parts) > 1 else []
                    
                    if len(args) < 1:
                        print("Использование: /sendfile [метка] <путь_к_файлу>")
                        print("Пример: /sendfile work ./doc.pdf")
                        print("Пример: /sendfile ./photo.jpg (метка будет 'default')")
                        continue

                    # Логика парсинга: если первый аргумент не похож на путь (не содержит / или .), считаем его меткой
                    # Но для простоты будем считать: если 2 аргумента, то первый - метка, второй - путь.
                    # Если 1 аргумент, то метка = 'default', путь = аргумент.
                    
                    tag = "default"
                    file_path = ""
                    
                    if len(args) == 1:
                        file_path = args[0]
                    elif len(args) >= 2:
                        tag = args[0]
                        file_path = args[1]
                    else:
                        print("Ошибка аргументов")
                        continue

                    space_obj = node.spaces[active_space_id]
                    
                    print(f"Отправка файла '{file_path}' с меткой '{tag}'...")
                    asyncio.create_task(space_obj.send_file(file_path, tag=tag))

                case '/logout':
                    if node.logout_user():
                        print("Выход выполнен")
                        await switch_space(None) # Сброс активного пространства
                    else:
                        print("Нет активного пользователя")

                case '/ssreg':
                    await node._ss_register_all()
                    print("Регистрация отправлена")

                case '/ssinfo':
                    for ss in node.signal_server_list:
                        status = node.signal_server_list[ss]['status']
                        print(f'{ss}: {"ONLINE" if status else "OFFLINE"}')
                
                case '/newspace': 
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    name = parts[1] if len(parts) > 1 else "DefaultSpace"
                    space_obj = await node.space_add(name)
                    if space_obj:
                        print(f"Пространство '{name}' создано. ID: {space_obj.space_id}")
                        # Автоматически переключаемся на новое пространство
                        await switch_space(space_obj.space_id)
                    else:
                        print("Ошибка создания пространства")

                case '/s_space':
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    if len(parts) < 2:
                        print("Использование: /s_space <space_id>")
                        continue
                    
                    target_id = parts[1]
                    if target_id in node.spaces:
                        await switch_space(target_id)
                    else:
                        print("Нет такого пространства")

                case "/send":
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    
                    # Отправляем в АКТИВНОЕ пространство
                    if not active_space_id or active_space_id not in node.spaces:
                        print("Ошибка: Не выбрано активное пространство. Используйте /s_space <id>")
                        continue
                    
                    if len(parts) < 2:
                        print("Использование: /send <message>")
                        continue
                    
                    message_text = parts[1]
                    space_obj = node.spaces[active_space_id]
                    res = await space_obj.send_message(message_text)
                    if not res: 
                        print("Ошибка отправки сообщения")

                case '/delspace': 
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    if len(parts) < 2:
                        print("Использование: /delspace <space_id>")
                        continue
                    
                    del_id = parts[1]
                    
                    # Если мы сейчас в этом пространстве, сбрасываем активное
                    if del_id == active_space_id:
                        await switch_space(None) 
                    
                    # Вызываем асинхронный метод
                    if await node.space_del(del_id):
                        print(f"Пространство '{del_id}' безопасно удалено")
                    else:
                        print("Не удалось удалить пространство (возможно, его нет)")
                    
                    del_id = parts[1]
                    if del_id == active_space_id:
                        await switch_space(None) # Сначала выходим из него
                    
                    if node.space_del(del_id):
                        print(f"Пространство '{del_id}' удалено")
                    else:
                        print("Не удалось удалить пространство")

                case '/listspace':
                    if not node.spaces:
                        print("Нет активных пространств")
                    else:
                        for sp_id, sp_obj in node.spaces.items():
                            marker = " <-- ACTIVE" if sp_id == active_space_id else ""
                            print(f"{sp_id[:16]}... : {sp_obj.name} {marker}")

                case '/connect': 
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    if len(parts) < 2:
                        print("Использование: /connect <space_id>")
                        continue
                    
                    target_id = parts[1]
                    print(f"Поиск и подключение к пространству '{target_id[:16]}...'...")
                    success = await node.connect_to_space(target_id)
                    
                    if success:
                        print("Подключение успешно!")
                        # Автоматически переключаемся на подключенное пространство
                        await switch_space(target_id)
                    else:
                        print("Не удалось подключиться к пространству")

                case '/s_user':
                    # Новая команда для просмотра пользователей в пространстве
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    
                    if len(parts) < 2:
                        # Если ID не указан, показываем пользователей в активном пространстве
                        target_id = active_space_id
                        if not target_id:
                            print("Укажите ID пространства или переключитесь в него через /s_space")
                            continue
                    else:
                        target_id = parts[1]

                    if target_id in node.spaces:
                        space = node.spaces[target_id]
                        print(f"\n--- Пользователи в пространстве '{space.name}' ({target_id[:8]}...) ---")
                        if not space.users:
                            print("  (пусто)")
                        else:
                            for u_key, u_data in space.users.items():
                                print(f"  ID: {u_key[:16]}...")
                                print(f"  Name: {u_data['name']}")
                                print(f"  Addr: {u_data['addr']}")
                                print(f"  Box Pub: {u_data['box_public_key'][:16]}...")
                                print("  --------------------------------")
                        print(f"Всего пользователей: {len(space.users)}\n")
                    else:
                        print("Пространство не найдено или не подключено")
                
                case '/info':
                    if node.User is None:
                        print("Нет активного пользователя.")
                    else:
                        u = node.User
                        print("=== Информация о пользователе ===")
                        print(f"Name: {u.profile.get('name')}")
                        print(f"Verify Key: {u.verify_key.encode().hex()[:32]}...")
                        print("=================================")

                case '/spaceinfo':
                    # Новая команда: подробная информация о пространстве
                    if node.User is None: 
                        print("Нужен пользователь"); continue
                    
                    if len(parts) < 2:
                        target_id = active_space_id
                        if not target_id:
                            print("Укажите ID пространства или переключитесь в него через /s_space")
                            continue
                    else:
                        target_id = parts[1]

                    if target_id in node.spaces:
                        space = node.spaces[target_id]
                        print(f"\n=== Информация о пространстве '{space.name}' ===")
                        print(f"Space ID   : {space.space_id}")
                        print(f"Local Addr : {space.addr} (Мой сокет)")
                        print(f"Admin?     : {space.ADMIN}")
                        print(f"secret?     : {space.secret.hex()}")
                        
                        # Метаданные (то, что видят другие)
                        meta = space.metadata
                        if meta:
                            print(f"Meta Name  : {meta.get('Name')}")
                            print(f"Meta Addr  : {meta.get('addr')} (Адрес для подключения других)")
                            print(f"Meta Key   : {meta.get('verify_key', '')[:32]}...")
                            print(f"Meta Secret: {meta.get('secret', '')}...")
                        else:
                            print("Metadata   : Нет (клиентский режим или не инициализировано)")
                            
                        print(f"Users Count: {len(space.users)}")
                        print("=====================================\n")
                    else:
                        print("Пространство не найдено")

                case '/exit':
                    print("Завершение работы...")
                    node._shutdown.set()
                    break

                case _:
                    print(f"Неизвестная команда: {cmd}")

        except EOFError:
            print("Ввод завершён (EOF)")
            node._shutdown.set()
            break
        except Exception as e:
            traceback.print_exc()
            print(f"Ошибка ввода: {e}")

    print("TUI остановлен.")


async def main():
    try:
        node = Node()
    except Exception as e:
        print(f"Ошибка инициализации Node: {e}")
        traceback.print_exc()
        return

    node_task = asyncio.create_task(node.start(), name='node_main')
    input_task = asyncio.create_task(input_loop(node), name='tui_input')

    try:
        await asyncio.wait([input_task], return_when=asyncio.FIRST_COMPLETED)
    except KeyboardInterrupt:
        print("\nПрервано пользователем")
    finally:
        await node.stop()
        print("Завершение работы.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass