class Space():
    seed =              None # Сид для улучшение криптографии
    space_id =          None # SHA256(seed) — публичный ID
    secret =            None # BLAKE2b(seed, key="chat-key", size=32) — ключ шифрования сообщений
    signing_key =       None # Ed25519 приватный ключ — для подписи метаданных (Не передаётся)
    verify_key =        None # Ed25519 публичный ключ
    metadata =      {        # В metadata можно написать всё что угодно, и потом всё сериализовать
        'Name':'ServerName'  # в строку json например, так как json не нужно собирать как protobuf 
    }                        #    
    signature =         None # Подписанная metadata
    event_log =         None # Лог событий, оставлю на пототм

    def __init__(self):
        pass