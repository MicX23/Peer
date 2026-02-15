import socket

class Space():
    seed                = None      # Сид для улучшение криптографии
    space_id            = None      # SHA256(seed) — публичный ID
    secret              = None      # BLAKE2b(seed, key="chat-key", size=32) — ключ шифрования сообщений
    signing_key         = None      # Ed25519 приватный ключ — для подписи метаданных (Не передаётся)
    verify_key          = None      # Ed25519 публичный ключ
    metadata = {                    # В metadata можно написать всё что угодно, и потом всё сериализовать
        'Name':'ServerName'         # в строку json например, так как json не нужно собирать как protobuf 
    }                               #    
    signature           = None      # Подписанная metadata
    event_log           = None      # Лог событий, оставлю на пототм
    sock                = None

    NODE                = None      # Нода для запроса 
    TUPE                = "client"  # Тип клиента? 
    # TODO:Наерное стоит сделать MySpace и Space


    def __init__(self, Node, TUPE="client", seed=None):
        if seed: self.load(seed)
        self.NODE = Node
        self.get_sock()

    def get_sock(self):                                 # Просим сокет у Ноды
        self.sock = self.NODE.get_sock(self.space_id)   
        # verify_key для поиска внешних соеденений в пиринг сервере 


    def set_secret(self, secret) -> bool:
        if self.TUPE != "Admin": return False
        self.secret = secret
        return True

    def load(self, seed):
        self.seed = seed
    
    def save(self):
        pass


