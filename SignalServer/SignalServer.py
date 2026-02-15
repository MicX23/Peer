import socket, get_me_logger, asyncio

class SignalServer():

    server_name =   "TestServer" #
    signing_key =           None # Ed25519 приватный ключ — для подписи метаданных (Не передаётся)
    verify_key  =           None # Ed25519 публичный ключ !verify_key = id_signal_server!

    sock        =           None # Сокет для подключения
    logger      =           None # Логи
    _tasks      =           None # Задачи

    _shutdown   = asyncio.Event() # Событие завершения программы 

    def __init__(self, port=23023):
        self.logger = get_me_logger.get_logger('SignalServer') # Создаём логгер                                
        self.port = port

        self.raw_packets = asyncio.Queue(maxsize=1000)         # Очередь для сырых пакетов
        self.packages_sending = asyncio.Queue(maxsize=1000)    # Очередь для отправки пакетов 

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

    def register_user(self):
        pass

    def authentication_user(self):
        pass

    async def listen_loop(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            try:
                data, addr = await asyncio.wait_for(self.loop.sock_recvfrom(self.sock,1024),timeout=0.2) # получаем пакет
                await self.raw_packets.put((data,addr)) # добавляем в очередь
            except asyncio.TimeoutError:
                continue

    async def processor_loop(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self.raw_packets.get()
            print(f"Пришёл пакет от {addr}: {data.decode('utf-8')}")
            await self.packages_sending.put(("Hello".encode('utf-8'),addr))

    async def sending_loop(self):
        while not self._shutdown.is_set(): # Пока событие _shutdown не начнётся.
            data, addr = await self.packages_sending.get()
            await self.loop.sock_sendto(self.sock, data, addr)

    async def _close(self):
        self.sock.close()
        #TODO Здесь можно закрыть БД



if __name__ == "__main__":
    testSignalServer = SignalServer()
    asyncio.run(testSignalServer.start())