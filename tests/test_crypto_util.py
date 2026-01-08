import base64
from unittest import TestCase

from remarkable.security.crypto_util import aes_decrypt, aes_encrypt


class TestCryptoUtil(TestCase):
    key = "#hello-aes-hello-aes-hello-aes##"
    plain_text = b"this is plaintext."
    expected_text = b"B2tf/oy8SGl1PWonFpku3aEMoGl1q4Uw24B0VX96L24=\n"

    def test_aes_encrypt(self):
        ciphertext = base64.encodebytes(aes_encrypt(self.plain_text, key=self.key, fill=True))
        assert self.expected_text == ciphertext

    def test_aes_decrypt(self):
        assert self.plain_text == aes_decrypt(base64.decodebytes(self.expected_text), self.key, strip=True)
