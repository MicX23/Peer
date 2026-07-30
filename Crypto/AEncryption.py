from nacl.public import PrivateKey, PublicKey, SealedBox
from nacl.encoding import HexEncoder

def generate_key() -> [PrivateKey, PrivateKey]:
    key = PrivateKey.generate()
    return [key, key.public_key]

def key_to_hex(key):
    return key.encode(encoder=HexEncoder)

def hex_to_public_key(hex):
    key = PublicKey(hex, encoder=HexEncoder)
    return key

def hex_to_private_key(hex):
    key = PrivateKey(hex, encoder=HexEncoder)
    return key

#---------------------/ запечатанный ящик /--------------------#

def sealbox_encrypt(pub_key, data:bytes) -> bytes:
    seal_box = SealedBox(pub_key)
    encrypt_data = seal_box.encrypt(data)
    return encrypt_data

def sealbox_decrypt(private_key, encrypt_data:bytes):
    seal_box = SealedBox(private_key)
    data = seal_box.decrypt(encrypt_data)
    return data 