import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from remarkable.security.package_encrypt import aes_dump, aes_load


def test_aes_dump_and_load():
    # Generate a random key for AESGCM
    key = os.urandom(32)
    aesgcm = AESGCM(key)

    # Test data
    test_data = {
        "string": "hello world",
        "number": 42,
        "boolean": True,
        "list": [1, 2, 3],
        "nested": {"key": "value"},
        "null": None
    }

    # Test encryption and decryption
    encrypted = aes_dump(aesgcm, data=test_data)
    decrypted = aes_load(aesgcm, data=encrypted)

    # Verify the decrypted data matches the original
    assert decrypted == test_data

    # Test with empty data
    empty_data = {}
    encrypted_empty = aes_dump(aesgcm, data=empty_data)
    decrypted_empty = aes_load(aesgcm, data=encrypted_empty)
    assert decrypted_empty == empty_data

    # Test with large data to verify chunking
    large_data = {"large": "x" * 10000}
    encrypted_large = aes_dump(aesgcm, data=large_data)
    decrypted_large = aes_load(aesgcm, data=encrypted_large)
    assert decrypted_large == large_data