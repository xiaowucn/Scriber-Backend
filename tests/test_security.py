import base64
import json

from remarkable.security.crypto_util import aes_encrypt, aes_decrypt


def test_encrypt_user():
    secret_key = "069f0ba4d5c635e9b98fb94b7cd98cc4"
    print("*" * 100)
    print(secret_key)
    user_info = {
        "uid": "1111111",
        "uname": "显示名称",
        "sys_code": "PIF",  # PIF, OAS, FMP
    }

    encrypt = base64.b64encode(
        aes_encrypt(json.dumps(user_info).encode("utf-8"), key=secret_key, fill=True)
    ).decode("utf-8")
    decrypt = json.loads(aes_decrypt(base64.b64decode(encrypt.encode("utf-8")), key=secret_key, strip=True))

    assert user_info == decrypt