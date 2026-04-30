import socket, get_me_logger, asyncio, json, nacl.signing, nacl.public
from nacl.exceptions import BadSignatureError

class SignalServer():

    server_name  =   "TestServer" #

    signing_key  =           None # Ed25519 приватный ключ — для подписи метаданных (Не передаётся)
    verify_key   =           None # Ed25519 публичный ключ !verify_key = id_signal_server!

    _box_private =           None # Приватный ключ шифрования (не передаётся)
    _box_public  =           None # Публичный ключ шифрования (передаётся в get_info)

    sock         =           None # Сокет для подключения
    logger       =           None # Логи
    _tasks       =           None # Задачи

    _shutdown   = asyncio.Event() # Событие завершения программы 

    def __init__(self, port=23023):
        self.logger = get_me_logger.get_logger('SignalServer') # Создаём логгер                                
        self.port = port

        if self.verify_key is None:
            self.signing_key = nacl.signing.SigningKey.generate()
            self.verify_key = self.signing_key.verify_key

        if self._box_public is None:
            self._box_private = nacl.public.PrivateKey.generate()
            self._box_public = self._box_private.public_key

        self.spaces_db = {}

        self.raw_packets = asyncio.Queue(maxsize=1000)         # Очередь для сырых пакетов
        self.packages_sending = asyncio.Queue(maxsize=1000)    # Очередь для отправки пакетов 

        self.users = {}

    async def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Создаём сокет
        self.sock.setblocking(False)                                 # Делаем сокет неблокируйщим
        self.sock.bind(('0.0.0.0', self.port))                       # Начинаем слушать указанный порт 
        self.logger.info(f"SignalServer binds in {self.port} port")  
        self.loop = asyncio.get_running_loop()

        self._tasks = [
            asyncio.create_task(self.listen_loop(),name='listen_loop'),
            asyncio.create_task(self.processor_loop(),name='processor_loop'),
            asyncio.create_task(self.sending_loop(),name='sending_loop')
        ]

        try:
            await self._shutdown.wait()     # Не даёт выполняться коду ниже 
        except asyncio.CancelledError:      # Ctrl+C вызывает исключение у Run
            self.logger.info("Initialization shutdown")
            self._shutdown.set()            # Ставим вручную 
        finally:
            # Завершаем выполнение 
            await self.stop()


    async def stop(self):
        self._shutdown.set()

        for task in self._tasks:
            if not task.done():
                task.cancel()
                self.logger.info(f"Task `{task.get_name()}` task cancel.")

        done, pending = await asyncio.wait(self._tasks, timeout=5, return_when=asyncio.ALL_COMPLETED) 

        for task in done:
            self.logger.info(f"{task.get_name()} task completed")

        for task in pending:
            self.logger.warning(f"{task.get_name()}: Execution exceeded time limit (5s)")
            task.cancel()

        await self._close()
        self.logger.info("Server stoped!")

    async def register_user(self, data:dict, addr):
        body = data.get('body', {})
        profile = body.get('profile')
        sig_hex = body.get('signature')

        # 1. Валидация полей
        if not profile or not sig_hex:
            await self.packages_sending.put((self._pack({"type": "error", "message": "Missing profile or signature"}).encode('utf-8'), addr))
            return

        user_vk_hex = profile.get('verify_key')
        if not user_vk_hex:
            await self.packages_sending.put((self._pack({"type": "error", "message": "Missing verify_key in profile"}).encode('utf-8'), addr))
            return

        # 2. Проверка подписи профиля клиентом
        try:
            user_verify_key = nacl.signing.VerifyKey(bytes.fromhex(user_vk_hex))
            
            # ВАЖНО: параметры json.dumps должны ТОЧНО совпадать с клиентскими
            profile_bytes = json.dumps(
                profile,
                sort_keys=True,
                separators=(',', ':'),
                ensure_ascii=False
            ).encode('utf-8')
            
            signature = bytes.fromhex(sig_hex)
            user_verify_key.verify(profile_bytes, signature)
        except (BadSignatureError, ValueError):
            await self.packages_sending.put((self._pack({"type": "error", "message": "Invalid profile signature"}).encode('utf-8'), addr))
            return

        # 3. Сохранение пользователя (ключ = verify_key)
        user_id = user_vk_hex
        self.users[user_id] = {
            "name": profile.get("name"),
            "verify_key": user_vk_hex,
            "box_public_key": profile.get("box_public_key")
        }
        self.logger.info(f"Пользователь '{profile.get('name')}' зарегистрирован (ID: {user_id[:16]}...)")

        # 4. Формируем ответ сервера
        raw_data = {
            "type": "register",
            "response": "ok",
            "body": {
                "name": profile.get("name"),
                "verify_key": user_vk_hex
            }
        }
        raw_json = json.dumps(raw_data, ensure_ascii=False, separators=(',', ':'))
        signed_msg = self.signing_key.sign(raw_json.encode('utf-8'))

        response = {
            "raw": raw_data,
            "signature": signed_msg.signature.hex()
        }
        await self.packages_sending.put((self._pack(response).encode('utf-8'), addr))

    async def space_add(self, data:dict, addr):
        user_id = data.get('user_id')
        payload_hex = data.get('payload')
        signature_hex = data.get('signature')

        if not user_id or not payload_hex or not signature_hex:
            self.logger.warning(f"Неполные данные для space_add от {addr}")
            await self.packages_sending.put(('{"type": "error", "message": "Incomplete data"}'.encode('utf-8'), addr))
            return
        try:
            if user_id not in self.users:
                self.logger.warning(f"Пользователь {user_id[:8]}... не найден в базе зарегистрированных")
                await self.packages_sending.put(('{"type": "error", "message": "User not registered"}'.encode('utf-8'), addr))
                return
            user_box_pub_hex = self.users[user_id].get('box_public_key')
            if not user_box_pub_hex:
                self.logger.warning(f"У пользователя {user_id[:8]}... отсутствует box_public_key")
                await self.packages_sending.put(('{"type": "error", "message": "Missing user box key"}'.encode('utf-8'), addr))
                return
            
            encrypted_bytes = bytes.fromhex(payload_hex)
            user_box_pub = nacl.public.PublicKey(bytes.fromhex(user_box_pub_hex))

            box = nacl.public.Box(self._box_private, user_box_pub)
            raw_data_bytes = box.decrypt(encrypted_bytes)

            #  Проверка подписи расшифрованных данны
            user_verify_key = nacl.signing.VerifyKey(bytes.fromhex(user_id))
            user_verify_key.verify(raw_data_bytes, bytes.fromhex(signature_hex))

            # Распаковка полезных данных
            raw_data = json.loads(raw_data_bytes.decode('utf-8'))

            space_info = raw_data.get('space', {})

            space_id = space_info.get('space_id')

            if not space_id:
                raise ValueError("No space_id in metadata")

            self.spaces_db[space_id] = {
                "admin_addr": addr,       # IP:Port админа (UDP endpoint)
                "admin_id": user_id,      # ID админа для проверки прав
                "metadata": space_info    # Публичные метаданные
            }

            self.logger.info(f"Пространство успешно расшифровано и проверено от {user_id[:8]}...")
            self.logger.info(f"Space Name: {space_info.get('Name')}, ID: {space_id}")

            response = {
                "type": "space_add_ok", 
                "message": "Space registered successfully"
            }
            await self.packages_sending.put((json.dumps(response).encode('utf-8'), addr))
            self.logger.info(self.spaces_db[space_id])

        except Exception as e:
            self.logger.error(f"Ошибка обработки space_add: {e}")
            await self.packages_sending.put(('{"type": "error", "message": "Decryption or verification failed"}'.encode('utf-8'), addr))


        await self.packages_sending.put(('{"type": "info", "message":"space_add"}'.encode('utf-8'),addr))

    async def space_find(self, data:dict, addr):
        space_id = data.get('space_id')
        task_id = data.get('task_id')
        
        if not space_id or space_id not in self.spaces_db:
            response = {"type": "space_find_error", "message": "Space not found", "task_id":task_id}
            await self.packages_sending.put((json.dumps(response).encode('utf-8'), addr))
            return

        space_info = self.spaces_db[space_id]
        # Возвращаем адрес админа и его публичный ключ (для шифрования handshake)
        # admin_id нужен клиенту, чтобы потом проверить подпись при handshake
        response = {
            "type": "space_found",
            "body": {
                "space_id": space_id,
                "admin_addr": list(space_info['admin_addr']), # [ip, port]
                "admin_id": space_info['admin_id'],           # verify_key hex
                "metadata": space_info['metadata'],            # Имя и прочее
                "task_id": task_id
            }
        }
        
        self.logger.info(f"Space {space_id} found by client {addr}")
        await self.packages_sending.put((json.dumps(response).encode('utf-8'), addr))

    async def get_info(self, addr):
        try:
            srv_sock_addr = self.sock.getsockname()
            ip = srv_sock_addr[0] if srv_sock_addr[0] != '0.0.0.0' else '127.0.0.1'
            port = srv_sock_addr[1]
        except Exception:
            ip, port = '127.0.0.1', self.port
        # Публичный ключ (если не инициализирован, ставим заглушку, чтобы не крашить)
        pub_key = self.verify_key.encode().hex() if self.verify_key else "uninitialized_key"
        box_public = self._box_public.encode().hex() if self._box_public else "uninitialized_box_key"
        response = {
            "type": "me_info",
            "body": {
                "name": self.server_name,
                "addr": [ip, port],
                "public_key": pub_key,
                "box_public": box_public
            }
        }
        # Упаковываем в bytes и отправляем в очередь отправки
        await self.packages_sending.put((self._pack(response).encode('utf-8'), addr))

    async def ping_pong(self, addr:tuple):
        await self.packages_sending.put(('{"type": "pong"}'.encode('utf-8'),addr))


    def _pack(self, data:dict) -> str:
        return json.dumps(data)
    
    def _unpack(self, data:str) -> dict:
        return json.loads(data)

    async def listen_loop(self): # Слушает соеденение 
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            try:
                data, addr = await asyncio.wait_for(self.loop.sock_recvfrom(self.sock,4096),timeout=0.2) # получаем пакет
                await self.raw_packets.put((data,addr)) # добавляем в очередь
            except asyncio.TimeoutError:
                continue

    async def processor_loop(self): # Обрабатывает пакеты 
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self.raw_packets.get()
            # self.logger.info(f"Пришёл пакет от {addr}: {data.decode('utf-8')}")

            data = await asyncio.to_thread(self._unpack, data)
            self.logger.info(f"Распакованная data это {type(data)}: {data}")
            if type(data) != dict:
                self.logger.warning(f"Unpacking data is not dict")
                continue
            elif not 'type' in data.keys():
                self.logger.warning(f"There is no 'type' attribute in data.\n {data.keys()}:{data}")
                continue
            
            match data['type']:
                case 'ping': await self.ping_pong(addr)
                case 'register': await self.register_user(data, addr)
                case 'space_add': await self.space_add(data, addr)
                case 'space_find': await self.space_find(data['body'], addr)
                case 'get_info': await self.get_info(addr)
                case _: await self.packages_sending.put(('{"type": "error"}'.encode('utf-8'),addr))

    async def sending_loop(self): # Отправляет пакеты 
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self.packages_sending.get()
            await self.loop.sock_sendto(self.sock, data, addr)

    async def _close(self):
        self.sock.close()
        #TODO Здесь можно закрыть БД



if __name__ == "__main__":
    testSignalServer = SignalServer()
    asyncio.run(testSignalServer.start())