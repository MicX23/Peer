import asyncio, get_me_logger
from User import User
from Crypto import Crypto

# Node - это Supervisor в системе; Управляет всем тем что нужно этой системе. 
# Node - It is the Supervisor of the system; It manages everything this system requires.


class Node:

    def __init__(self, host_queues):
        self.logger     = get_me_logger.get_logger('Node') # Ссылка на логгер 

        self._storage   = None                       # Ссылка на модуль хранения данных
        self._user      = User(self._storage, 
                                    self.logger)     # Ссылка на модуль пользывателя 
        self._crypro    = Crypto()                   # Ссылка на модуль шифрования
        self._networker = None                       # Ссылка на модуль работы с сетью              

        # События \ Events
        self.shutdown  = asyncio.Event()             # Системное событие для завершение работы 
        self.user_loaded = asyncio.Event()           # Событие загрузки пользывателя 

        # Очереди \ Queues
        self._events    = asyncio.Queue(maxsize=300) # Очередь системный событий 
        self._host_q    = host_queues                # Очередь событий в UI

        self._spaces    = {}        # Словарь пространств \
        self._contact   = {}        # Список контактов
        self._tasks     = []        # Запущенные задачи \

    async def start(self) -> None:
        self.logger.debug(self.user_loaded.is_set())
        self._spawn(self._init_modules(), 'init_modules')
        self._spawn(self._service_deamon(), 'service_daemon')
        # возможно по завершению инициализации модулей возвращать ChatManger, а shudown вывести в отдельный демон?
        try:
            await self.shutdown.wait()
        except asyncio.CancelledError:
            self.logger.info('Start больше не выполняется :\\, скорее всего кто то не вызвал request_shutdown в конце выполнения, или не обраотал какую то ошибку.')
        await self.stop()

    async def stop(self):
        self.logger.debug("Node shutdown!")

    def request_shutdown(self):
        self.logger.debug("Node start shutdown")
        self.shutdown.set()
        

    #-----------------/ Spaces metod /--------------------# 

    async def add_space(self) -> bool:
        pass

    async def del_space(self) -> bool:
        pass

    #--------------------/ Service /----------------------# 
    def _spawn(self, coro, name: str) -> asyncio.Task: # добавляет демоны в _tasks
        task = asyncio.create_task(coro, name=name)
        task.add_done_callback(self._tasks.remove)
        self._tasks.append(task)
        return task

    async def _init_modules(self):
        await self._start_user()
        await self.user_loaded.wait()

        self.logger.debug('Modules loaded!')

    async def _start_user(self):
        if self.user_loaded.is_set(): return
        if await self._user.start() == 0:
            self.user_loaded.set()
            await self._host_q.put({'type':'user_loadet'})
        else: 
            self.logger.debug('user not found')
            await self._host_q.put({'type':'user_not_loadet'})

    def create_user(self):
        private_key, public_key, verify_key, sign_key = self._crypro.create_profile()
        req = self._user.create_user(private_key, public_key, verify_key, sign_key)
        self.logger.debug(f"User created:{req}")
        if req: self.user_loaded.set()

    
    async def _service_deamon(self) -> None:
        while not self.shutdown.is_set():
            try:
                data = await asyncio.wait_for(self._events.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue

            match data['type']:
                case _: pass


    