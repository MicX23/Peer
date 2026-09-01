import asyncio, socket
from . import stun_request

# INFO: Использывать 1 порт как для лс так и для пространств? Или делить запросы на группы? Или вообще у каждого пространства свой порт (это затрпатн так то)?

class NetWorker:
    def __init__(self, logger, s_events, h_events):
        self.timeout        = 5 # secund 
        self.is_global_IP   = False # Белый или серый ip
        self.logger         = logger

        self._system_events = s_events
        self._host_events   = h_events

        self.__direct_sock_init()

    def __direct_sock_init(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('', 0))
        self.direct_info = self.sock.getsockname()

        self.sock.settimeout = self.timeout
        self.sock.setblocking = False

        self.logger.info(f'Direct message socket running on {self.direct_info}')

    def _first_stun_request(self):
        stun_request.get_me_addr(self.sock, self.logger)


    async def _keep_a_live_stun(self): 
        # Отправляем регулярно, так как если пир отключться то мапинг проподёт, хотя он ещё будет как минимум 30 секунд, 
        # можно отправить с адреса KAL пакет, скорее всего он отпраит тот же пакет!
        # Вообще хорошей практикой будет просто уменьшить количество пакетов в минуту для тех, у кого есть соеденения!

        pass

    
