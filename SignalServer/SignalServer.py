import socket, sqlite3, logger

class SignalServer():

    Name =          "TestServer" #
    signing_key =           None # Ed25519 приватный ключ — для подписи метаданных (Не передаётся)
    verify_key =            None # Ed25519 публичный ключ !verify_key = id_signal_server!

    Logger =                None # логи

    Conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Сокет для подключения

    def __init__(self, port=23023):
        self.Logger = logger.get_logger('SignalServer')
        self.Conn.bind(('0.0.0.0', port))
        self.Logger.info(f"SignalServer binds in {port} port")

        self.__close()

    def RegisterUser(self):
        pass

    def AuthenticationUser(self):
        pass

    def __listen(self):
        pass

    def __close(self):
        self.Conn.close()



if __name__ == "__main__":
    testSignalServer = SignalServer()