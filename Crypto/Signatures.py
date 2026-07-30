from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError
from nacl.encoding import HexEncoder

# Модуль для подписания и проверки 

def generate_signature() -> [SigningKey, VerifyKey]:
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key
    return [signing_key, verify_key]

def hex_to_verefy_key(hex):
    key = VerifyKey(hex, encoder=HexEncoder)
    return key

def hex_to_signing_key(hex):
    key = SigningKey(hex, encoder=HexEncoder)
    return key

def sign(data:bytes, signing_key):
    signed = signing_key.sign(data)
    return signed.signature.hex()

def verify(data:bytes, verify_key, signed):
    try:
        verify_key.verify(data, signed)
        return True
    except BadSignatureError:
        return False

