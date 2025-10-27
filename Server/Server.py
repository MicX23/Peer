class Server: 
    #####################
    TChannels = []      # Только информация для соеденения 
    VChannels = []      #
    #####################
    
    Host = ('0.0.0.0',0) # Информация о Хосте

    ServerHASH = 'HASH'
    MessagesSent = 0

    def getInfoTC(self, id) -> dict:
        # Возвращает информацию о тестовом канале
        pass

    def getInfoVC(self, id) -> dict:
        # Возвращает информацию о голосовм канале
        pass

    def getHeaderChannels(self) -> dict:
        # Возвращает название всех каналов:
        # {
        #   'TChannels':['Name1', 'Name2', 'Name3'],
        #   'VChannels':['Name1', 'Name2']
        # }
        pass

    def newTChannels(self, info):
        # Добавляет новый текстовый канал
        pass
    def newVChannels(self, info):
        # Добавляет новый голосовой канал
        pass

    def checkInfo(self):
        # Использует внутреннию информацию для проверки данных, например о каналах(и не только), у хоста.
        pass

    def deliteServer(self):
        pass
