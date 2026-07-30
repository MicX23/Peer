from . import AEncryption, Signatures
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
import asyncio

class Crypto:
    def __init__(self):
        self.is_loaded = asyncio.Event() # изменить на profile_is_loaded

    def create_profile(self):
        private_key, public_key = AEncryption.generate_key()
        signing_key, verify_key = Signatures.generate_signature()
        return [private_key.encode(encoder=HexEncoder).decode('utf-8'), 
        public_key.encode(encoder=HexEncoder).decode('utf-8'), 
        signing_key.encode(encoder=HexEncoder).decode('utf-8'), 
        verify_key.encode(encoder=HexEncoder).decode('utf-8')]

    def load_profile(self, private_key_hex, public_key_hex, signing_key_hex, verify_key_hex):
        self.private_key = AEncryption.hex_to_private_key(private_key_hex)
        self.public_key = AEncryption.hex_to_public_key(public_key_hex)
        self.signing_key = Signatures.hex_to_signing_key(signing_key_hex)
        self.verify_key = Signatures.hex_to_verefy_key(verify_key_hex)
        self.is_loaded.set()

    def sign(self, data:str):
        if not self.is_loaded.is_set():
            # logger.error("Профиль не загружен")
            print("Профиль не загружен")
            return
        return Signatures.sign(data.encode('utf-8'),self.signing_key)

    def verify(self, data, verify_key_hex, signed_hex):
        if type(data) == str: data = data.encode('utf-8')
        elif type(data) != str: 
            print('data не byte и не str')
            return None
        verify_key = Signatures.hex_to_verefy_key(verify_key_hex) # Это трудоёмкая задача, если сообщений будет много, то нужно куда то сохранять типа {'id':VerefyKey}
        return Signatures.verify(data,verify_key,bytes.fromhex(signed_hex))

    def encrypt(self, data, key_hex, in_sealbox:bool=False):
        if type(data) == str: data = data.encode('utf-8')
        elif type(data) != str: 
            print('data не byte и не str')
        if in_sealbox:
            public_key = AEncryption.hex_to_public_key(key_hex)
            return AEncryption.sealbox_encrypt(public_key,data)
        else:
            return "Не готово"

    def decrypt(self, encrypt_data:bytes, key=None):
        if not self.is_loaded.is_set():
            # logger.error("Профиль не загружен")
            print("Профиль не загружен")
            return
        if key == None:
            return AEncryption.sealbox_decrypt(self.private_key, encrypt_data)

