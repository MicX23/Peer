import socket, asyncio, json
from core.get_me_logger import get_logger
from core.User import User
from core.Space import Space

class Node():

    public_addr = ('0.0.0.0',0)
    conn        = None
    User        = None
    

    signal_server_list = {
        ('127.0.0.1', 23023): {
            'status': False,           # Статус доступности сервера
            'public_key': None,       # Публичный ключ сессии (Box public key)
        }
    }

    spaces = {}


    def __init__(self, addr=('127.0.0.1',0)):
        self.logger = get_logger('Node')
        self.public_addr = addr
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False) 
        self.sock.bind(self.public_addr)

        self.spaces: dict[str, Space] = {}

        self._tasks = []
        self._shutdown = asyncio.Event()

        self._packages_public_sending = asyncio.Queue(maxsize=1000)
        self._packages_public_responses = asyncio.Queue(maxsize=1000)
        self._service_queue = asyncio.Queue(maxsize=300)

        self.logger.info(f'Node started, addr = [{self.public_addr}]')

        self.count_task = 0



        self.User = User.load()  # Автоматически грузит, если файл один
        if self.User and not self.set_user(self.User):
            self.logger.info(f'User is not loaded')
            self.User = None
        else: self.logger.info(f'User is loaded')


    async def start(self):
        while self.User is None:
            # self.logger.debug("Ожидание инициализации пользователя...")
            await asyncio.sleep(0.5)  # Пауза чтобы не грузить цикл

        self.loop = asyncio.get_running_loop() 
            
        self.logger.info(f'Node async started')
        self._tasks = [
            asyncio.create_task(self._net_public_sender_deamon(), name='pub_sender'),
            asyncio.create_task(self._net_public_listen_deamon(), name='pub_listener'),
            asyncio.create_task(self._net_public_processor(), name='pub_processor'),
            asyncio.create_task(self.__ss_service_deamon(), name='ss_monitor'),
            asyncio.create_task(self.__service_deamon(), name='service_processor'),
            # ... добавляй остальные демоны здесь ...
        ]
        self.logger.info(f"Запущено {len(self._tasks)} фоновых задач")


        await self._shutdown.wait()
    

    async def create_task_deamon(self, task, t_name):
        task = asyncio.create_task(task(), name=t_name)
        self._tasks.append(task)
        return task
        
    async def stop(self):
        self.logger.info("Остановка Node...")
        self._shutdown.set()
        
        # Отменяем все задачи
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Ждём завершения с таймаутом
        if self._tasks:
            done, pending = await asyncio.wait(self._tasks, timeout=5, return_when=asyncio.ALL_COMPLETED)
            for task in pending:
                self.logger.warning(f"Задача {task.get_name()} не завершилась за 5с, принудительная отмена")
                task.cancel()
        
        # Закрываем ресурсы
        if hasattr(self, 'sock') and self.sock:
            self.sock.close()
        
        self.logger.info("Node остановлен")


################# [ SIGNAL SERVER ] ################

    async def _ss_get_info_all(self):
        for ss in self.signal_server_list.keys():
            await self._packages_public_sending.put(('{"type":"get_info"}'.encode(),ss))


    async def _ss_get_info(self, addr):
        await self._packages_public_sending.put(('{"type":"get_info"}'.encode(),addr))

    async def _ss_register_all(self):
        if self.User is None:
            self.logger.debug("register_on_server: нет активного пользователя")
            return False
        
        payload = {
            "type": "register",
            "body": {
                "profile": self.User.profile,
                "signature": self.User.profile_signature
            }
        }

        encoded = await asyncio.to_thread(self.net_pack, payload)
        for ss in self.signal_server_list.keys():
            if self.signal_server_list[ss]['status']:
                await self._packages_public_sending.put((encoded.encode('utf-8'), ss))
                self.logger.info(f"Отправлен запрос регистрации на {ss}")
        return True

    async def _ss_register(self, server_addr):
        if self.User is None:
            self.logger.debug("register_on_server: нет активного пользователя")
            return False
        
        
        if server_addr not in self.signal_server_list:
            self.logger.debug(f"register_on_server: сервер {server_addr} не в списке")
            return False
        
        payload = {
            "type": "register",
            "body": {
                "profile": self.User.profile,
                "signature": self.User.profile_signature
            }
        }

        encoded = await asyncio.to_thread(self.net_pack, payload)
        await self._packages_public_sending.put((encoded.encode('utf-8'), server_addr))
        self.logger.info(f"Отправлен запрос регистрации на {server_addr}")
        return True

    async def ss_info_reg(self, body, addr):
        if (body['addr'][0],body['addr'][1]) == addr:
            for attr in body.keys():
                self.signal_server_list[addr][attr] = body[attr]
        self.logger.info(body)



    async def ss_public_space(self, space_id):
        if self.User is None:
            self.logger.debug("ss_public_space: нет активного пользователя")
            return False
        
        space = self.spaces.get(space_id)
        if not space:
            self.logger.warning(f"ss_public_space: Пространство {space_id} не найдено")
            return False
        
        raw_data = {
            "space": space.metadata,
            "signature": space.signature
        }

        raw_data_bytes = await asyncio.to_thread(self.net_pack, raw_data)
        raw_data_bytes = raw_data_bytes.encode('utf-8')
        signed_obj = self.User.signing_key.sign(raw_data_bytes)

        for server_addr, info in self.signal_server_list.items():
            if not info.get('status'):
                continue

            ss_pub_key_hex = info.get('box_public')
            if not ss_pub_key_hex:
                self.logger.warning(f"Нет публичного ключа для SS {server_addr}. Пропуск.")
                continue

            try:
                import nacl.public
                server_pub_key = nacl.public.PublicKey(bytes.fromhex(ss_pub_key_hex))
                box = nacl.public.Box(self.User.box_key, server_pub_key)
                encrypted_payload = box.encrypt(raw_data_bytes)

                

                outer_packet = {
                    "user_id": self.User.verify_key.encode().hex(), # Кто отправил?
                    "type": "space_add",                            # Что делаем?
                    "payload": encrypted_payload.hex(),             # Данные в hex (или base64)
                    "signature": signed_obj.signature.hex()         # Подпись данных
                }

                packet_to_send = await asyncio.to_thread(self.net_pack, outer_packet)
                packet_to_send = packet_to_send.encode('utf-8')

                packet_str = await asyncio.to_thread(self.net_pack, outer_packet)
                packet_bytes = packet_str.encode('utf-8')
                
                # ПРОВЕРКА РАЗМЕРА
                if len(packet_bytes) > 1400:
                    self.logger.warning(f"Пакет слишком большой для UDP ({len(packet_bytes)} байт)! Возможна потеря данных.")
                    # Для отладки можно вывести содержимое начала и конца
                    self.logger.debug(f"Начало: {packet_str[:100]}...")
                    self.logger.debug(f"Конец: ...{packet_str[-100:]}")

                await self._packages_public_sending.put((packet_to_send, server_addr))
                self.logger.info(f"Пространство {space_id} зашифровано и отправлено на SS {server_addr}")
            except Exception as e:
                self.logger.error(f"Ошибка шифрования для SS {server_addr}: {e}")


    def ss_ping(self, addr: tuple) -> bool:
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            conn.settimeout(10)
            # conn.setblocking(False)
            conn.sendto(b'{"type": "ping", "addr": ["127.0.0.1", 23023]}', addr)

            data, c_addr = conn.recvfrom(4096)
            if c_addr == addr: 
                if data == '{"type": "ping", "addr": ["127.0.0.1", 23023]}': 
                    self.logger.info(f"Server {addr}: True")
                    return True
                else: 
                    self.logger.info(f"Server {addr}: {data}.")
            return True

        except TimeoutError:
            self.logger.info(f"Server {addr}: Timeout error.")
            return False
        except ConnectionResetError:
            self.logger.info(f"Server {addr}: Connection error.")
            return False
        finally:
            conn.close()


    async def __ss_connection_check(self):
        for ss in self.signal_server_list.keys():
            self.signal_server_list[ss]['status'] = await asyncio.to_thread(self.ss_ping, ss)


    async def __ss_service_deamon(self): 
        self.logger.info(f"Check Signal Servers")
        await self.__ss_connection_check()
        await self._ss_get_info_all()
        self.logger.info(f"Checkin Signal Servers: Done")
        # и alive пакеты


################ [ SEARVICE DEAMON ] ###############

    # _packages_public_sending   - очередь для отпраки сообщений хранит картежи (data, addr)
    # _packages_public_responses - очередь для принятый сырых пакетов 
    # _service_queue             - очередь для выполнения серверсных команд 

    async def _net_public_sender_deamon(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self._packages_public_sending.get()
            self.logger.info(f"отправляю {data} на {addr}")
            await self.loop.sock_sendto(self.sock, data, addr)

    async def _net_public_listen_deamon(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            try:
                data, addr = await asyncio.wait_for(self.loop.sock_recvfrom(self.sock,4096),timeout=0.2) # получаем пакет
                await self._packages_public_responses.put((data,addr)) # добавляем в очередь
            except asyncio.TimeoutError:
                continue

    async def _net_public_processor(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self._packages_public_responses.get()
            self.logger.info(f"Пришёл пакет от {addr}: {data.decode('utf-8')}")

            data = await asyncio.to_thread(self.net_unpack, data)

            msg_type = data.get('type')
            body = data.get('body', {})

            match msg_type:
                case 'me_info': await self.ss_info_reg(body, addr)
                case 'space_add_ok': self.logger.info(f"Space зарегистрирован")
                case 'space_find_error':
                    await self._service_queue.put({'type':'space_find_error', "task_id": data["task_id"]})
                case 'space_found': 
                    await self._service_queue.put({'type':'space_found', 
                                                   "task_id": body["task_id"],
                                                   "space": {
                                                       "space_id": body["space_id"],
                                                        "admin_addr": body["admin_addr"],
                                                        "admin_id": body["admin_id"],
                                                        "metadata": body["metadata"]
                                                   } 
                                                   })
    



    async def __service_deamon(self):
        tasks = {}
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data = await self._service_queue.get()
            match data['type']:
                case 'add_task': 
                    tasks[data['task']["task_id"]] = {'type':data['task']["type"] , "space_id":data['task']["space_id"]}
                    self.logger.info(f"Доабвленна задача {tasks[data['task']["task_id"]]}")
                case 'space_find_error':
                    del tasks[data["task_id"]]
                case 'space_found':
                    del tasks[data["task_id"]]
                    await self.__add_space_new(data["space"])

        

    def net_pack(self, data:dict) -> str:
        return json.dumps(data)
    
    def net_unpack(self, data:str) -> dict:
        return json.loads(data)
    
    def get_me_sock(self) -> tuple:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind(('127.0.0.1', 0))
        addr = sock.getsockname()
        return sock, addr
    
    async def connect_to_space(self, space_id: str):
        if not self.User:
            self.logger.warning("Нельзя подключиться: нет активного пользователя")
            return None
        
        target_ss = None
        for ss_addr, info in self.signal_server_list.items():
            if info.get('status'):
                target_ss = ss_addr
                break
        if not target_ss:
            self.logger.warning("Нет активных Signal Servers")
            return None
        
        self.logger.info(f"Поиск пространства {space_id} на SS {target_ss}...")
        request = {
            "type": "space_find",
            "body": {
                "space_id": space_id,
                "task_id": self.count_task
            }
        }

        await self._packages_public_sending.put((json.dumps(request).encode('utf-8'), target_ss))
        await self._service_queue.put({'type':'add_task', 'task':{"task_id": self.count_task,'type':'space_find',"space_id": space_id,}})
        self.count_task = self.count_task + 1

        self.count_task = self.count_task + 1
        return True

##################### [ USER ] #####################

    def create_user(self, name: str, user_id: str = "default") -> bool:
        # Создать нового пользователя и добавить его в Node.
        if self.User is not None:
            return False
        
        new_user = User(name)  # verify_key сгенерируется внутри
        if self.set_user(new_user):
            # Имя файла для сохранения = hex(verify_key)
            new_user.save()  # без аргументов, user_id берётся из ключа
            return True
        return False

    def logout_user(self):
        if self.User is None:
            return False
    
        if self.User.is_loaded:
            self.User.save()
        
        self.User = None
        self.logger.info("Пользователь выполнен выход (logout)")
        return True

    def edit_user(self):pass

    def set_user(self, user: User) -> bool:
        # Добавляет пользователя после проверки.
        if self.__test_user(user):
            self.User = user
            return True
        return False
    
    def __test_user(self, user: User) -> bool:
        # Тихая проверка пользователя перед добавлением в Node. Возвращает True если пользователь валиден.
        try:
            # Минимальные проверки:
            if not hasattr(user, 'profile'):
                return False
            if not isinstance(user.profile, dict):
                return False
            if 'name' not in user.profile or not user.profile['name']:
                return False
            if not hasattr(user, 'verify_key') or user.verify_key is None:
                return False
            if user.profile.get('verify_key') != user.verify_key.encode().hex():
                return False

            import nacl.public
            from nacl.exceptions import BadSignatureError


            # 1. Тест подписи
            test_sign_msg = b"node_self_test_sign"
            signed = user.signing_key.sign(test_sign_msg)
            # verify бросает BadSignatureError при неверной подписи
            user.verify_key.verify(signed.message, signed.signature)

            # 2. Тест шифрования (Box)
            test_enc_msg = b"node_self_test_encrypt"
            box = nacl.public.Box(user.box_key, user.box_public_key)
            encrypted = box.encrypt(test_enc_msg)
            decrypted = box.decrypt(encrypted)

            if decrypted != test_enc_msg:
                self.logger.debug(f"__test_user: Ошибка расшифровки (данные не совпадают)")
                return False

            return True

        except BadSignatureError:
            self.logger.debug("__test_user: Ошибка верификации подписи")
            return False
        except Exception as e:
            self.logger.debug(f"__test_user: Криптографический тест не пройден: {e}")
            return False
        except Exception:
            return False  # Любая ошибка = невалидный пользователь
        
#################### [ SPACE ] ####################

    async def space_add(self, name: str) -> Space | None:
        """Создаёт пространство локально (режим админа) и сохраняет."""
        if not self.User:
            self.logger.debug("__space_add: нет активного пользователя")
            return None
            
        space = Space(node=self, is_admin=True, name=name)
        self.spaces[space.space_id] = space
        self.logger.info(f"Пространство создано: {name} ({space.space_id[:8]}...)")
        await self.ss_public_space(space.space_id)
        await space.start()
        return space

    async def space_del(self, space_id: str) -> bool:
        if space_id not in self.spaces:
            self.logger.warning(f"Попытка удалить несуществующее пространство {space_id}")
            return False
            
        space = self.spaces[space_id]
        
        # Удаляем из словаря СРАЗУ, чтобы новые входящие пакеты или команды 
        # не пытались использовать уже удаляемое пространство.
        del self.spaces[space_id]
        
        # Запускаем процесс корректного закрытия в фоне, 
        # чтобы не блокировать выполнение основного кода, если это важно.
        # Но лучше сделать await, если мы хотим гарантировать порядок.
        try:
            await space.leave_space()
            self.logger.info(f"Пространство {space_id} успешно удалено и закрыто.")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при удалении пространства {space_id}: {e}", exc_info=True)
            # Даже если ошибка, пространство уже удалено из self.spaces
            return False
    
    async def __add_space_new(self, data: dict):
        space_id = data.get('space_id')
        admin_addr = tuple(data.get('admin_addr'))
        admin_id = data.get('admin_id')
        metadata = data.get('metadata', {})
        self.logger.info(f"metadata: {metadata}")
        space_addr = tuple(metadata.get('addr'))

        self.logger.info(f"Инициализация подключения к Space: {metadata.get('Name')} ({space_id[:8]}...)")
        self.logger.info(f"Адрес Space: {space_addr}")

        new_space = Space(node=self, is_admin=False, name=metadata.get('Name', 'Unknown'))
        try:
            if await new_space.to_connect(metadata):
                self.spaces[new_space.space_id] = new_space
        except TimeoutError:
            # Ловим таймаут конкретно здесь
            self.logger.warning(f"Таймаут при подключении к Space {metadata.get('Name')}. Адрес: {metadata.get('addr')}")
            
        except Exception as e:
            # Ловим любые другие ошибки сети
            self.logger.error(f"Ошибка при добавлении Space {metadata.get('Name')}: {e}", exc_info=True)


        
################## [ DATA BASE ] ##################
    def __db_connect(self): pass

    def __db_save_user(self): pass
    def __db_save_space(self): pass
    def __db_save_signal_server(self): pass

    def __db_load_user(self): pass
    def __db_load_space(self): pass
    def __db_load_signal_server(self): pass




if __name__ == '__main__':
    node = Node()
    asyncio.run(node.start())
