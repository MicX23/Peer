from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
import message_pb2

class Essence(): # По сути User
    signing_key = None              # Закрый ключ для подписи сообщений (НЕ отправлять)
    verify_key = None        # Открытый ключ для подписи сообщений

    profiles = {
        "indeficator" : {           # У каждого сервера свой профиль
            "name": "Anonim1",      # Имя сущьности
            "images": b"1"          # Аватар
        },
        "1" : {                     # У каждого сервера свой профиль
            "name": "Anonim2",      # Имя сущьности
            "images": b"1"          # Аватар
        },
        "2" : {                     # У каждого сервера свой профиль
            "name": "Anonim3",      # Имя сущьности
            "images": b"1"          # Аватар
        }
    }

    def __init__(self):
        if not self.load():
            self.signing_key = SigningKey.generate()
            self.verify_key = self.signing_key.verify_key

##################################< Profile >#####################################

    def get_profile(self, id:str) -> dict:
        for i in self.profiles.keys():
            if i == id: return self.profiles[i]
        return None
        
    def set_profile(self, id:str, name:str=None, avatar:bytes=None) -> bool:
        for i in self.profiles.keys():
            if i == id: 
                self.profiles[i] = {           
                    "name": name,               # Имя сущьности
                    "images": avatar            # Аватар
                }
                return True
        return False

    def add_profile(self, idf:str, name:str=None, avatar:bytes=None) -> bool:
        if idf in self.profiles.keys(): 
            print("Log add_profile: Уже существует")
            return False
        self.profiles.update({idf:{"name": name, "images": avatar}})
        return True
            
    def del_profile(self, idf:str) -> bool:
        try:
            self.profiles.pop(idf)
        except KeyError:
            print("Log del_profile: Нет такого профиля")
            return False
        if idf in self.profiles.keys(): return False
        else: return True

###################################< ProtoBuf >###################################
    def PB_get_profile(self, id:str) -> bytes:
        profile = self.get_profile(id)
        if profile == None: return None
        pb_profile = message_pb2.Profile()
        pb_profile.name = profile["name"]
        pb_profile.avatar = profile["images"]
        profile_signature = self.to_sign(pb_profile.SerializeToString())

        pb_essence = message_pb2.EssenceInfo()
        pb_essence.verify_key = self.verify_key.encode()
        pb_essence.profile.CopyFrom(pb_profile)
        pb_essence.profile_signature = profile_signature
        return pb_essence.SerializeToString()
        
##################################< Sign >########################################

    def to_sign(self, data:bytes) -> bytes:              # Подпись пользывателя
        return self.signing_key.sign(data).signature

##################################< Saves >#######################################

    def load(self) -> bool:
        return False
    
    def save(self) -> bool:
        return False
    
#################################< Tests >########################################


def verify_profile(data: bytes) -> bool:
    if data is None:
        return False

    essence = message_pb2.EssenceInfo()
    essence.ParseFromString(data)

    verify_key = VerifyKey(essence.verify_key)
    try:
        verify_key.verify(essence.profile.SerializeToString(), essence.profile_signature)
        # print("Подпись действительна")
        return True

    except BadSignatureError:
        # print("Подпись недействительна")
        return False

    

def Tests():
    tt = Essence()
    print(tt.get_profile("1"))
    print(tt.set_profile("1", "YA"))
    # Дебаги print(tt.get_profile("1"))
    print(tt.add_profile("3", "YA1", "djndfj".encode()))
    # Дебаги print(tt.get_profile("3"))
    print(tt.del_profile("3"))
    # Дебаги print(tt.get_profile("3"))
    print("PB sector")
    data = tt.PB_get_profile("2")
    if data == None: print("PB_get_profile: Error")
    elif verify_profile(data) == True: print("PB_get_profile: True")



if __name__ == "__main__": Tests()

    