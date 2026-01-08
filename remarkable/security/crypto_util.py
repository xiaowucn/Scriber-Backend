from base64 import b64decode, b64encode

import jwt
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
from Crypto.PublicKey import RSA

from remarkable.config import get_config


def aes_encrypt(plaintext, key, fill=False):
    key = key.encode("utf8")
    blocksize = 16
    reminder_len = len(plaintext) % blocksize
    reminder = b""
    if reminder_len > 0:
        if fill:
            plaintext += b"\0" * (blocksize - reminder_len)
        else:
            plaintext, reminder = plaintext[:-reminder_len], plaintext[-reminder_len:]
    aes = AES.new(key, AES.MODE_CBC, key[11:27])
    return aes.encrypt(plaintext) + reminder


def aes_decrypt(ciphertext, key, strip=False):
    key = key.encode("utf8")
    blocksize = 16
    reminder_len = len(ciphertext) % blocksize
    if not strip and reminder_len > 0:
        ciphertext, reminder = ciphertext[:-reminder_len], ciphertext[-reminder_len:]
    else:
        reminder = b""
    aes = AES.new(key, AES.MODE_CBC, key[11:27])

    if strip:
        return aes.decrypt(ciphertext).rstrip(b"\0")
    return aes.decrypt(ciphertext) + reminder


def rsa_encrypt(plaintext: str, key: str, length=117, encoding="utf-8") -> str:
    """
    length = rsa_public_key.size_in_bits()/8-11 , 1024长度的密钥为117
    """
    res = []
    plaintext = plaintext.encode(encoding)
    rsa_public_key = RSA.importKey(key)
    cipher = PKCS1_cipher.new(rsa_public_key)
    for i in range(0, len(plaintext), length):
        res.append(cipher.encrypt(plaintext[i : i + length]))
    return b64encode(b"".join(res)).decode(encoding)


def rsa_decrypt(ciphertext: str, key: str, length=128, encoding="utf-8"):
    res = []
    rsa_private_key = RSA.importKey(key)
    cipher = PKCS1_cipher.new(rsa_private_key)
    ciphertext = b64decode(ciphertext)
    for i in range(0, len(ciphertext), length):
        res.append(cipher.decrypt(ciphertext[i : i + length], 0))
    return b"".join(res).decode(encoding)


def encode_jwt(payload: dict, key: str = None, algorithm="HS256") -> str:
    return jwt.encode(payload, key or get_config("app.jwt_secret_key"), algorithm=algorithm)


def make_bearer_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
