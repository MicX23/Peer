import hashlib, json, nacl.signing, nacl.utils, asyncio, socket, nacl.secret, nacl.exceptions, os, uuid, datetime 
from core.get_me_logger import get_logger

class Space:
    # Только для Admin
    seed        = None
    signing_key = None
    space_id    = None

    # И для Admin, и для Client
    secret      = None
    verify_key  = None
    _metadata   = None
    signature   = None
    sock        = None
    
    NODE        = None
    ADMIN       = False 

    users       = {}

    def __init__(self, node, is_admin: bool, name: str = "Unnamed Space"):
        self.NODE = node
        self.ADMIN = is_admin
        self._metadata = {"Name": name} 


        self.download_dir = os.path.join("./downloads", self.name.replace(" ", "_"))
        os.makedirs(self.download_dir, exist_ok=True)

         # Словарь для сборки файлов: { file_id: { "chunks": {}, "total": N, "name": str } }
        self._receiving_files = {} 
        
        # Создаем сокет
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setblocking(False)
        self.sock.bind(('127.0.0.1', 0))
        self.addr = self.sock.getsockname()
        
        self.logger = get_logger(f"[S]{name}")
        self.logger.info(f"Инициализация пространства '{name}'. Локальный адрес: {self.addr}")

        self._packages_sending = asyncio.Queue(maxsize=1000)
        self._packages_responses = asyncio.Queue(maxsize=1000)
        self.messages = asyncio.Queue(maxsize=1000)
        self.events = asyncio.Queue(maxsize=1000)
        
        self._shutdown = asyncio.Event()
        self._connected_event = asyncio.Event() # Событие успешного подключения для клиента
        
        self.loop = None 
        self._tasks = []
        self.users = {}
        
        if self.ADMIN:
            self._init_admin()
            # Админ считается подключенным сразу после инициализации
            self._connected_event.set()

    def _init_admin(self):
        self.seed = nacl.utils.random(32)
        self.space_id = hashlib.sha256(self.seed).hexdigest()
        self.signing_key = nacl.signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.secret = hashlib.blake2b(
            self.seed, key=b"chat-key", digest_size=32).digest()
        
        self._metadata["space_id"] = self.space_id
        self._metadata["verify_key"] = self.verify_key.encode().hex()
        self._metadata["addr"] = list(self.addr)
        self._metadata["secret"] = self.secret.hex()      
    
        self._sign_metadata()

    @property
    def name(self):
        return self._metadata['Name']
    
    @property
    def metadata(self):
        return dict(self._metadata) if self._metadata else None

    def update_metadata(self, key: str, value):
        if not self.ADMIN:
            raise PermissionError("Только админ может менять метаданные")
        self._metadata[key] = value
        self._sign_metadata()

    def encrypt_message(self, message: bytes) -> bytes:
        if not self.secret:
            raise RuntimeError("Пространство не инициализировано (нет secret)")
        box = nacl.secret.SecretBox(self.secret)
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        encrypted = box.encrypt(message, nonce)
        return nonce + encrypted.ciphertext

    def decrypt_message(self, encrypted_package: bytes) -> bytes:
        if not self.secret:
            raise RuntimeError("Пространство не инициализировано (нет secret)")
        box = nacl.secret.SecretBox(self.secret)
        nonce_size = nacl.secret.SecretBox.NONCE_SIZE
        if len(encrypted_package) < nonce_size:
            raise ValueError("Пакет слишком короткий")
        nonce = encrypted_package[:nonce_size]
        ciphertext = encrypted_package[nonce_size:]
        return box.decrypt(ciphertext, nonce)

    def _sign_metadata(self): 
        meta_bytes = json.dumps(self.metadata, sort_keys=True, separators=(',', ':')).encode('utf-8')
        signed = self.signing_key.sign(meta_bytes)
        self.signature = signed.signature.hex()

    async def to_connect(self, data: dict) -> bool:
        if self.ADMIN:
            raise RuntimeError("to_connect() недоступен для Admin.")

        try:
            secret = bytes.fromhex(data['secret'])
            verify_key = nacl.signing.VerifyKey(bytes.fromhex(data['verify_key']))
        except ValueError as e:
            self.logger.error(f"Неверный формат ключей: {e}")
            return False

        self._metadata['Name'] = data['Name']
        self._metadata["space_id"] = data['space_id']
        self._metadata["verify_key"] = data['verify_key']
        self._metadata["secret"] = data['secret']

        self.secret = secret
        self.verify_key = verify_key
        self.space_id = data['space_id']

        addr = tuple(data['addr']) if isinstance(data['addr'], list) else data['addr']

        await self.start()

        connect_req = {
            "type": "connect",
            "space_id": self.space_id,
            "user": self.NODE.User.profile
        }
        
        packed_req = await asyncio.to_thread(self.net_pack, connect_req)
        encrypted_req = self.encrypt_message(packed_req.encode())
        
        self.logger.info(f"=== ОТПРАВКА CONNECT ===")
        self.logger.info(f"Цель: {addr}")
        self.logger.info(f"Мой порт: {self.addr}")
        self.logger.info(f"Размер пакета: {len(encrypted_req)} байт")
        
        try:
            await self.loop.sock_sendto(self.sock, encrypted_req, addr)
            self.logger.info(f"Пакет успешно отправлен в сокет")
        except Exception as e:
            self.logger.error(f"Ошибка отправки пакета: {e}", exc_info=True)
            return False

        self.logger.info(f"Ожидание ответа... (таймаут 5с)")
        
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=5.0)
            self.logger.info(f"=== ПОДКЛЮЧЕНИЕ УСПЕШНО ===")
            return True
        except asyncio.TimeoutError:
            self.logger.warning(f"=== ТАЙМАУТ ПОДКЛЮЧЕНИЯ ===")
            self.logger.warning(f"Проверьте, запущен ли Админ на {addr}")
            self.logger.warning(f"Проверьте логи Админа на наличие 'ПОЛУЧЕН CONNECT'")
            await self.stop()
            return False

    async def start(self):
        if not self.loop:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                if hasattr(self.NODE, 'loop') and self.NODE.loop:
                    self.loop = self.NODE.loop
                else:
                    raise RuntimeError("No running event loop found")
        
        self.logger.info(f"{self.name} Запуск демонов пространства...")
        
        self._tasks = [
            await self.NODE.create_task_deamon(self.__space_sender_deamon, f"{self.name}_sender"),
            await self.NODE.create_task_deamon(self.__space_listen_deamon, f"{self.name}_listener"),
            await self.NODE.create_task_deamon(self.__space_processor_deamon, f"{self.name}_processor")
        ]

    async def leave_space(self):
        self.logger.info(f"Инициирован выход из пространства '{self.name}'")
        
        # 1. Отправляем уведомление об уходе, если сокет еще жив и мы не админ (или админ тоже должен уведомить)
        if not self._shutdown.is_set() and self.sock:
            try:
                leave_msg = {
                    "type": "leave",
                    "space_id": self.space_id,
                    "user": self.NODE.User.profile if self.NODE.User else None
                }
                packed = await asyncio.to_thread(self.net_pack, leave_msg)
                encrypted = self.encrypt_message(packed.encode())
                
                # Отправляем всем известным пользователям
                for uid, u_data in list(self.users.items()):
                    try:
                        addr = tuple(u_data['addr']) if isinstance(u_data['addr'], list) else u_data['addr']
                        await self.loop.sock_sendto(self.sock, encrypted, addr)
                        self.logger.debug(f"Отправлено leave пользователю {uid}")
                    except Exception as e:
                        self.logger.warning(f"Не удалось отправить leave пользователю {uid}: {e}")
            except Exception as e:
                self.logger.error(f"Ошибка при отправке уведомления о выходе: {e}")

        # 2. Вызываем стандартную остановку (остановка демонов и закрытие сокета)
        await self.stop()
        self.logger.info(f"Пространство '{self.name}' полностью закрыто.")

    # Обновим метод stop, чтобы он гарантированно закрывал сокет
    async def stop(self):
        if self._shutdown.is_set():
            return # Уже останавливается
            
        self.logger.info(f"{self.name} Остановка процессов...")
        self._shutdown.set()
        
        # Ждем завершения задач
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        if self._tasks:
            # gather с return_exceptions=True важен, чтобы отмена задач не вызывала краш
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        # Закрываем сокет
        if self.sock:
            try:
                self.sock.close()
                self.logger.debug(f"Сокет пространства {self.name} закрыт.")
            except Exception as e:
                self.logger.error(f"Ошибка при закрытии сокета: {e}")
            finally:
                self.sock = None

    async def __space_sender_deamon(self):
        while not self._shutdown.is_set():
            try:
                data, addr = await asyncio.wait_for(self._packages_sending.get(), timeout=0.5)
                if addr is not None:
                    await self.loop.sock_sendto(self.sock, data, addr)
                else:
                    # Рассылка всем пользователям
                    for uid, m_data in list(self.users.items()):
                        try:
                            await self.loop.sock_sendto(self.sock, data, tuple(m_data['addr']))
                        except Exception as e:
                            self.logger.warning(f"Ошибка отправки пользователю {uid}: {e}")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if not self._shutdown.is_set():
                    self.logger.error(f"Ошибка в sender_deamon: {e}")

    async def __space_listen_deamon(self):
        while not self._shutdown.is_set():
            try:
                data, addr = await asyncio.wait_for(
                    self.loop.sock_recvfrom(self.sock, 4096), 
                    timeout=0.5
                )
                self.logger.info(f"LISTENER: Получен сырой UDP пакет от {addr} ({len(data)} байт)")
                await self._packages_responses.put((data, addr))
                m_data = self.decrypt_message(data)
                self.logger.info(f"data: {m_data}")

                
            except asyncio.TimeoutError:
                continue
            except OSError:
                break
            except Exception as e:
                if not self._shutdown.is_set():
                    self.logger.error(f"Ошибка в listen_deamon: {e}")
            except nacl.exceptions.CryptoError:
                    self.logger.info(f"Я не смог")
                    pass
            
    async def send_leave_signal(self):
        """Отправляет уведомление всем участникам о выходе из чата."""
        if not self.secret or not self.NODE.User:
            return

        data = {
            "type": "leave",
            "space_id": self.space_id,
            "user": self.NODE.User.profile # Передаем свой профиль, чтобы другие знали, кто ушел
        }
        
        try:
            packed = await asyncio.to_thread(self.net_pack, data)
            encrypted = self.encrypt_message(packed.encode())
            # Рассылаем всем текущим пользователям
            await self._packages_sending.put((encrypted, None)) 
            self.logger.info("Сигнал leave отправлен участникам")
        except Exception as e:
            self.logger.error(f"Ошибка отправки сигнала leave: {e}") 

    async def __space_processor_deamon(self):
         self.logger.info("PROCESSOR DEMON STARTED") # <--- Проверка запуска
         while not self._shutdown.is_set():
            try:
                # Ждем пакет из очереди
                data, addr = await asyncio.wait_for(self._packages_responses.get(), timeout=0.5)
                
                self.logger.info(f"PROCESSOR: Извлек пакет из очереди от {addr}. Размер: {len(data)}")

                try:
                    # Попытка расшифровать
                    self.logger.debug("Попытка расшифровки...")
                    decrypted_bytes = self.decrypt_message(data)
                    self.logger.debug("Расшифровка успешна")
                    
                    data_str = decrypted_bytes.decode('utf-8')
                    unpacked_data = await asyncio.to_thread(self.net_unpack, data_str)
                    
                    msg_type = unpacked_data.get('type')
                    self.logger.info(f"PROCESSOR: Тип сообщения: {msg_type}")
                    
                    match msg_type: 
                        case "connect":
                            self.logger.warning(f"!!! ОБНАРУЖЕН CONNECT ОТ {addr} !!!")
                            # Ответ админа
                            message = {
                                "type": "connect_true",
                                "space_id": self.space_id,
                                "user": self.NODE.User.profile, 
                                "users": self.users
                            }
                            packed_msg = await asyncio.to_thread(self.net_pack, message)
                            encrypted_msg = self.encrypt_message(packed_msg.encode())
                            
                            self.logger.info(f"Отправляю connect_true обратно на {addr}")
                            await self._packages_sending.put((encrypted_msg, addr))
                            
                            # Добавляем клиента
                            metadata = unpacked_data.get("user")
                            if metadata:
                                self.users[metadata['verify_key']] = {
                                    'name': metadata['name'], 
                                    'box_public_key': metadata['box_public_key'], 
                                    'addr': addr
                                }
                                self.logger.info(f"Клиент {metadata['name']} добавлен в список пользователей")

                                await self.events.put({
                                        "type": "user_connected",
                                        "user_id": metadata['verify_key'],
                                        "name": metadata['name'],
                                        "addr": addr,
                                        "timestamp": asyncio.get_event_loop().time()
                                    })

                        case "good":
                            self.logger.debug(f"Получено подтверждение good от {addr}")

                        case "leave":
                            self.logger.info("Получен сигнал отключения (leave)")
                            user_profile = unpacked_data.get('user')
                            
                            if user_profile:
                                vk = user_profile.get('verify_key')
                                user_name = user_profile.get('name', 'Unknown')
                                
                                if vk and vk in self.users:
                                    # Удаляем пользователя из списка
                                    del self.users[vk]
                                    self.logger.info(f"Пользователь {user_name} покинул пространство.")
                                    
                                    # Отправляем событие в UI
                                    await self.events.put({
                                        "type": "user_disconnected",
                                        "user_id": vk,
                                        "name": user_name,
                                        "timestamp": asyncio.get_event_loop().time()
                                    })
                                else:
                                    self.logger.debug(f"Пользователь {user_name} не найден в списке активных (уже отключился?)")
                            continue

                        case "connect_true":
                            self.logger.info("!!! ПОЛУЧЕН CONNECT_TRUE ОТ АДМИНА !!!")
                            # Добавляем Админа в список пользователей
                            metadata = unpacked_data.get("user")
                            if metadata:
                                self.users[metadata['verify_key']] = {
                                    'name': metadata['name'], 
                                    'box_public_key': metadata['box_public_key'], 
                                    'addr': addr
                                }
                                self.logger.info(f"Админ {metadata['name']} добавлен в контакты")
                            
                            # Обрабатываем список других пользователей, если админ их прислал
                            users_list = unpacked_data.get("users", {})
                            if users_list:
                                self.logger.info(f"Получен список пользователей от админа: {len(users_list)} чел.")
                                # Отправляем им уведомление о нашем появлении
                                await self._notify_users(users_list)
                            
                            # САМОЕ ВАЖНОЕ: Сообщаем методу to_connect, что подключение успешно
                            self._connected_event.set()
                            self.logger.info("Событие подключения установлено. To_connect разблокирован.")
                        

                        case "message":
                            # Проверка, что сообщение из нашего пространства
                            if unpacked_data.get('space_id') != self.space_id:
                                self.logger.debug(f"Игнорирую сообщение из чужого пространства {unpacked_data.get('space_id')}")
                                continue 
                            
                            message = unpacked_data.get('message')
                            sender_id = unpacked_data.get('sender_id')
                            await self.messages.put((sender_id, message))
                            
                        case "in_new":
                            metadata = unpacked_data.get("user")
                            if metadata:
                                self.logger.info(f"Новый пользователь (in_new): {metadata['name']}")
                                self.users[metadata['verify_key']] = {
                                    'name': metadata['name'], 
                                    'box_public_key': metadata['box_public_key'], 
                                    'addr': addr
                                }

                                await self.events.put({
                                    "type": "user_joined",
                                    "user_id": metadata['verify_key'],
                                    "name": metadata['name'],
                                    "addr": addr
                                })

                                resp = {
                                    "type": "good",
                                    "space_id": self.space_id,
                                    "user": self.NODE.User.profile
                                }
                                packed_resp = await asyncio.to_thread(self.net_pack, resp)
                                enc_resp = self.encrypt_message(packed_resp.encode())
                                await self._packages_sending.put((enc_resp, addr))
                        
                        case "file_chunk":
                            transfer_id = unpacked_data.get('transfer_id')
                            chunk_index = unpacked_data.get('chunk_index')
                            total_chunks = unpacked_data.get('total_chunks')
                            file_name = unpacked_data.get('file_name')
                            tag = unpacked_data.get('tag', 'default')
                            data_hex = unpacked_data.get('data')
                            sender_id = unpacked_data.get('sender_id')
                            
                            if transfer_id not in self._receiving_files:
                                self._receiving_files[transfer_id] = {
                                    "chunks": {},
                                    "total": total_chunks,
                                    "name": file_name,
                                    "tag": tag,
                                    "received_count": 0,
                                    "sender_id": sender_id
                                }
                                # Можно вывести лог о начале приема, если нужно
                                # self.logger.info(f"Прием файла: {file_name} (Tag: {tag})")

                            file_info = self._receiving_files[transfer_id]
                            
                            try:
                                chunk_bytes = bytes.fromhex(data_hex)
                                # Проверка на дубликаты чанков
                                if chunk_index not in file_info["chunks"]:
                                    file_info["chunks"][chunk_index] = chunk_bytes
                                    file_info["received_count"] += 1
                                    
                                    if file_info["received_count"] == file_info["total"]:
                                        self._assemble_file(transfer_id, file_info)
                                        
                            except Exception as e:
                                self.logger.error(f"Ошибка чанка: {e}")
                            continue

                        case _:
                            self.logger.warning(f"Неизвестный тип сообщения: {msg_type}")

                except nacl.exceptions.CryptoError:
                    # Игнорируем пакеты, которые не можем расшифровать (не тот ключ)
                    # self.logger.debug(f"Игнорирую пакет с неверным ключом от {addr}")
                    pass
                
                except ValueError as e:
                    # Ошибка расшифровки
                    self.logger.error(f"ОШИБКА РАСШИФРОВКИ от {addr}: {e}")
                    self.logger.error(f"Возможно, неверный ключ secret. Мой secret hex: {self.secret.hex()[:16]}...")
                except Exception as e:
                    self.logger.error(f"Ошибка обработки пакета: {e}", exc_info=True)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if not self._shutdown.is_set():
                    self.logger.error(f"Критическая ошибка в processor: {e}", exc_info=True)
    

    def _assemble_file(self, transfer_id: str, file_info: dict):
        """Собирает файл и сохраняет по пути: Project_Root/downloads/DDMMYYYY/tag/filename"""
        try:
            # 1. Сортируем и собираем байты
            sorted_chunks = sorted(file_info["chunks"].items(), key=lambda x: x[0])
            file_content = b"".join([chunk for _, chunk in sorted_chunks])
            
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            if not os.path.exists(os.path.join(project_root, 'backend')) and not os.path.exists(os.path.join(project_root, 'electron')):
                 pass 

            # 3. Формируем дату (ДДММГГГГ)
            now = datetime.datetime.now()
            date_folder = now.strftime("%d%m%Y") 
            
            # 4. Получаем метку и имя файла
            tag = file_info.get("tag", "untagged")
            file_name = file_info["name"]
            
            # Очищаем метку от опасных символов
            safe_tag = "".join(c for c in tag if c.isalnum() or c in "._- ")
            safe_tag = safe_tag.strip()
            if not safe_tag:
                safe_tag = "untagged"

            # 5. Формируем полный АБСОЛЮТНЫЙ путь
            # Структура: Project_Root/downloads/DDMMYYYY/tag/filename
            downloads_dir = os.path.join(project_root, "downloads")
            final_path = os.path.join(downloads_dir, date_folder, safe_tag, file_name)
            
            # Создаем директорию рекурсивно
            os.makedirs(os.path.dirname(final_path), exist_ok=True)
            
            # Если файл уже есть, добавляем индекс
            if os.path.exists(final_path):
                base, ext = os.path.splitext(final_path)
                counter = 1
                while os.path.exists(final_path):
                    final_path = f"{base}_{counter}{ext}"
                    counter += 1

            # 6. Записываем файл
            with open(final_path, 'wb') as f:
                f.write(file_content)
                
            self.logger.info(f"Файл сохранен (ABSOLUTE): {final_path}")
            
            # Уведомляем UI
            # ВАЖНО: Мы отправляем АБСОЛЮТНЫЙ путь
            asyncio.create_task(self.events.put({
                "type": "file_received",
                "file_name": file_name,
                "path": final_path, # <-- Абсолютный путь
                "size": len(file_content),
                "tag": safe_tag,
                "sender_id": file_info.get("sender_id")
            }))
            
            # Очищаем память
            if transfer_id in self._receiving_files:
                del self._receiving_files[transfer_id]
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения файла {transfer_id}: {e}", exc_info=True)
            
    async def _notify_users(self, users: dict):
        """
        Отправляет уведомление in_new всем пользователям из списка.
        Не ждет ответа в блокирующем режиме, просто отправляет.
        Добавление в self.users происходит, когда мы получим 'good' обратно (или можно добавить сразу).
        """
        notify_payload = {
            "type": "in_new",
            "space_id": self.space_id,
            "user": self.NODE.User.profile
        }
        
        packed_notify = await asyncio.to_thread(self.net_pack, notify_payload)
        encrypted_notify = self.encrypt_message(packed_notify.encode())

        for user_key, userdata in users.items():
            u_addr = tuple(userdata['addr']) if isinstance(userdata['addr'], list) else userdata['addr']
            self.logger.info(f"Отправляю in_new пользователю {userdata.get('name')} на {u_addr}")
            await self._packages_sending.put((encrypted_notify, u_addr))
            
            # ВАЖНО: Мы добавляем пользователя в список СРАЗУ, так как доверяем списку от Админа.
            # Если он не ответит 'good', он просто не будет знать о нас, но мы будем знать о нем.
            # При отправке сообщений мы будем пытаться стучаться к нему.
            if user_key not in self.users:
                self.users[user_key] = userdata

    async def send_message(self, message: str) -> bool:
        if not self.secret:
            return False

        data = {
            "type": "message",
            "message": message,
            "space_id": self.space_id,
            "sender_id": self.NODE.User.verify_key.encode().hex()
        }
        try:
            packed = await asyncio.to_thread(self.net_pack, data)
            encrypted = self.encrypt_message(packed.encode())
            await self._packages_sending.put((encrypted, None))
            return True
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return False
        
    async def send_file(self, file_path: str, tag: str = "default"):
        """
        Разбивает файл на чанки и отправляет их.
        :param file_path: Путь к файлу
        :param tag: Метка для папки (например, 'work', 'memes')
        """
        if not os.path.exists(file_path):
            self.logger.error(f"Файл не найден: {file_path}")
            return False

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        # Генерируем уникальный ID передачи
        transfer_id = str(uuid.uuid4())[:8]
        
        CHUNK_SIZE = 1000 
        
        self.logger.info(f"Начинаю отправку файла: {file_name} (Tag: {tag})")
        
        with open(file_path, 'rb') as f:
            chunk_index = 0
            total_chunks = (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE else 0)

            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                
                packet = {
                    "type": "file_chunk",
                    "transfer_id": transfer_id, # Уникальный ID этой сессии передачи
                    "file_name": file_name,
                    "tag": tag,                 # Метка для папки
                    "chunk_index": chunk_index,
                    "total_chunks": total_chunks,
                    "data": data.hex(),
                    "sender_id": self.NODE.User.verify_key.encode().hex()
                }
                
                packed = await asyncio.to_thread(self.net_pack, packet)
                encrypted = self.encrypt_message(packed.encode())
                
                await self._packages_sending.put((encrypted, None))
                
                chunk_index += 1
                # Небольшая пауза, чтобы не перегружать UDP буфер
                await asyncio.sleep(0.005) 
                
        self.logger.info(f"Отправка файла {file_name} завершена.")
        return True

    def net_pack(self, data:dict) -> str:
        return json.dumps(data)
    
    def net_unpack(self, data:str) -> dict:
        return json.loads(data)