from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
import json, os

# User это просто хранилище данных о пользователе

class User(): 

    signing_key = None      # Закрый ключ для подписи сообщений (НЕ отправлять)
    verify_key  = None      # Открытый ключ для подписи сообщений используется как id

    profile     = {}        # Профиль, методанные  TODO: так как делаю для диплома будет только 1, потом нужно поравить и сделать для каждого сервера

    def __init__(self):
        if not self.load():
            self.signing_key = SigningKey.generate()
            self.verify_key = self.signing_key.verify_key
            self.profile['name'] = 'New user'
            self.save()
        else: print('Данные загрузились')   # Это в логи 

        print(self.profile)

    def load(self): # нет обработки исключений
        if not os.path.isdir('user'): return False
        with open('user/private.key','rb') as file:
            self.signing_key = SigningKey(file.read())
        with open('user/public.key','rb') as file:
            self.verify_key = VerifyKey(file.read())
        with open('user/profile.json','r') as file:
            self.profile = json.loads(file.read())
        return True
    
    def save(self): # нет обработки исключений
        if not os.path.exists('user'): os.mkdir('user')
        with open('user/private.key','wb') as file:
            file.write(self.signing_key.encode())
        with open('user/public.key','wb') as file:
            file.write(self.verify_key.encode())
        with open('user/profile.json','w') as file:
            file.write(json.dumps(self.profile))

# Должен уметь подписывать и проверять документы как в TestUser

if __name__ == "__main__": 
    us = User()
