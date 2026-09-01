

class ChatManager:
    def __init__(self,logger, s_event, h_event, net_worker):
        self.logger         = logger
        
        self._system_events = s_events
        self._host_events   = h_events
        self._net_worker    = net_worker
         