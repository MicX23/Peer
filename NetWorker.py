import get_me_logger, socket, asyncio

class NetWorker:

    def __init__(self):
        self.public_addr            = ('ip',0)                      # Публичный адрес 
        self.private_addrs          = []                            # Список приватных адресов
        self._signal_servers        = []                            # Список адресов сигнальных серверов

        self._q_packages_received   = asyncio.Queue(maxsize=1000)   # 
        self._q_packages_sending    = asyncio.Queue(maxsize=1000)   #
        self._q_service             = asyncio.Queue(maxsize=1000)   #

    async def start(self):
        pass

    async def send_direct_message(self,message,contact):
        # зашифровываем
        # отправляем контакту
        pass   

    async def send_space_message(self,message,peers):
        # зашифровываем
        # отправляем всем пирам
        pass   


    #-------------------------/ Service /---------------------------#\

    async def _demon_listener(self):        # Слушает порты и отправляет сырые пакеты в процессор
        pass

    async def _demon_processor(self):       # Обрабатывает пакеты
        pass
    # keep_a_live пакеты кто отправляет? 
    async def _demon_sender(self):          # Отправляет пакеты из очереди
        pass

    async def _demon_service(self):         # Обрабатывает служебные запросы из q_service
        pass

    #-----------------------/ SignalServer /-------------------------#\

    async def _ss_register(self):           # Подключается к серверам из списка 
        pass

    async def _ss_search_user(self):        # Изщет пользывателя для связи
        pass

    async def _ss_connect_to_space(self):   # Запрос на подключение к пространству  
        pass

    async def _ss_register_a_space(self):   # Зарегестрировать своё пространство  
        pass

    #--------------------/ Straight сonnection /---------------------#\

    async def _sc_create_tunnel(self):      # Прямое подулючение к друг другу 
        pass

    # [!Note]
    # Вообще подумать как создавать приглошения, как их упаковывать и передавать...
    #