import json
import os
import time
import zlib
from base64 import b64decode, b64encode
from typing import Any

import msgspec
from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from utensils.crypto import JHexSm4

NONCE_SIZE = 12
CHUNK_SIZE = 4096 - 64
AAD = b"extra_auth_data="


class PackageEncrypt:
    def __init__(self, key):
        if isinstance(key, str):
            key = key.encode()
        self.secret_key = key[:16].ljust(16, b"\0")
        self.iv_key = key[::-1][:16].ljust(16, b"\0")

    def encrypt(self, data):
        data = zlib.compress(data)
        aes = AES.new(self.secret_key, AES.MODE_CBC, self.iv_key)
        if isinstance(data, dict):
            data = json.dumps(data)
        padding_size = 16 - (len(data) + 1) % 16
        if padding_size == 16:
            padding_size = 0
        data = b"".join((hex(padding_size)[2:].encode(), data))
        if padding_size:
            data = data.ljust(len(data) + padding_size, b"\0")
        return aes.encrypt(data)

    def encrypt_json(self, json_data):
        str_data = json.dumps(json_data).encode("utf-8")
        return self.encrypt(str_data)

    def decrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        aes = AES.new(self.secret_key, AES.MODE_CBC, self.iv_key)
        data = aes.decrypt(data)
        padding_size = int(chr(data[0]), 16)
        data = data[1:]
        if padding_size:
            data = data[:-padding_size]
        data = zlib.decompress(data)
        return data

    def decrypt_json(self, data):
        return json.loads(self.decrypt(data))


class AES256GCMEncryptor:
    def __init__(self, key: bytes | str):
        if isinstance(key, str):
            key = key.encode()
        self.key = key[:32].ljust(32, b"\0")

    def encrypt(self, data: bytes | str):
        if isinstance(data, str):
            data = data.encode()
        nonce = os.urandom(12)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return nonce + ciphertext + tag

    def decrypt(self, encrypted: str | bytes):
        if isinstance(encrypted, str):
            encrypted = encrypted.encode()
        nonce = encrypted[:12]
        ciphertext = encrypted[12:-16]
        tag = encrypted[-16:]  # 前端tag在最后
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag).decode()

    def encrypt_json(self, json_data):
        str_data = msgspec.json.encode(json_data)
        return self.encrypt(str_data)

    def decrypt_json(self, data):
        return msgspec.json.decode(self.decrypt(data))


class HexSm4Encryptor:
    def __init__(self, hex_key: str):
        assert len(bytes.fromhex(hex_key)) == 16
        self.hex_key = hex_key

    def encrypt(self, hex_data: str):
        return JHexSm4.encrypt(hex_data, self.hex_key)

    def decrypt(self, hex_data: str):
        return JHexSm4.decrypt(hex_data, self.hex_key)

    def encrypt_json(self, json_data):
        str_data = msgspec.json.encode(json_data)
        return bytes.fromhex(self.encrypt(str_data))

    def decrypt_json(self, data):
        if isinstance(data, bytes):
            data = data.hex()
        return msgspec.json.decode(self.decrypt(data))


def aes_dump(aesgcm: AESGCM, *, data: Any) -> bytes:
    serialized = msgspec.json.encode(data)
    nonce = os.urandom(NONCE_SIZE)
    associated_data = f"{round(time.time())}".encode()
    encrypted = aesgcm.encrypt(nonce, serialized, associated_data=associated_data)
    encoded = b64encode(nonce + encrypted + AAD + associated_data)
    return b"".join(encoded[i : i + CHUNK_SIZE] for i in range(0, len(encoded), CHUNK_SIZE))


def aes_load(aesgcm: AESGCM, *, data: bytes) -> Any:
    decoded = b64decode(data)
    nonce = decoded[:NONCE_SIZE]
    aad_starts_from = decoded.find(AAD)
    associated_data = decoded[aad_starts_from:].replace(AAD, b"") if aad_starts_from != -1 else None
    encrypted_session = decoded[NONCE_SIZE:aad_starts_from]
    decrypted = aesgcm.decrypt(nonce, encrypted_session, associated_data=associated_data)
    return msgspec.json.decode(decrypted)
