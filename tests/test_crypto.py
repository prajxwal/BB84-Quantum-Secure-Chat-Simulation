"""
Tests for Crypto Module (encryption, utils, key manager)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from src.crypto.utils import (
    text_to_binary, binary_to_text, binary_to_hex, hex_to_binary,
    bits_to_string,
)
from src.crypto.key_manager import KeyManager, EncryptionKey, KeyExhaustedError
from src.crypto.encryption import encrypt_message, decrypt_message, xor_bits


# ─── Utils Tests ────────────────────────────────────────────────

def test_text_to_binary():
    """Text to binary conversion."""
    bits = text_to_binary("A")
    assert bits == [0, 1, 0, 0, 0, 0, 0, 1]


def test_binary_to_text():
    """Binary to text conversion."""
    bits = [0, 1, 0, 0, 0, 0, 0, 1]  # 'A'
    assert binary_to_text(bits) == "A"


def test_text_binary_roundtrip():
    """Text → binary → text should be identity."""
    messages = ["Hello!", "BB84 Quantum", "Test 123 !@#", ""]
    for msg in messages:
        bits = text_to_binary(msg)
        result = binary_to_text(bits)
        assert result == msg, f"Roundtrip failed for '{msg}': got '{result}'"


def test_binary_hex_roundtrip():
    """Binary → hex → binary should be identity."""
    bits = [1, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1]
    hex_str = binary_to_hex(bits)
    result = hex_to_binary(hex_str)
    assert result == bits


def test_xor_bits():
    """XOR should work correctly."""
    a = [1, 0, 1, 0]
    b = [1, 1, 0, 0]
    assert xor_bits(a, b) == [0, 1, 1, 0]


# ─── Key Manager Tests ─────────────────────────────────────────

def test_encryption_key_consume():
    """Key should track bit consumption."""
    key = EncryptionKey([1, 0, 1, 1, 0, 0, 1, 0])
    consumed = key.consume(3)
    assert consumed == [1, 0, 1]
    assert key.bits_used == 3
    assert key.remaining() == 5


def test_encryption_key_exhausted():
    """Should raise when key is exhausted."""
    key = EncryptionKey([1, 0, 1])
    key.consume(3)
    with pytest.raises(KeyExhaustedError):
        key.consume(1)


def test_key_manager_set_and_get():
    """KeyManager should store and retrieve keys."""
    km = KeyManager()
    km.set_key([1, 0, 1, 0, 1, 0, 1, 0])
    key = km.get_key()
    assert key is not None
    assert key.length == 8


def test_key_manager_rotation():
    """Key should indicate rotation needed at 75% usage."""
    km = KeyManager()
    km.set_key([1] * 100)
    km.consume_bits(75)
    assert km.needs_rotation()


def test_key_manager_clear():
    """Clear should zero out key bits."""
    km = KeyManager()
    km.set_key([1, 1, 1, 1])
    km.clear()
    assert km.get_key() is None


# ─── Encryption/Decryption Tests ───────────────────────────────

def test_encrypt_decrypt_roundtrip():
    """Encrypt then decrypt should return original message."""
    from src.bb84.protocol import generate_random_bits
    key_bits = generate_random_bits(256)

    km_encrypt = KeyManager()
    km_encrypt.set_key(list(key_bits))

    km_decrypt = KeyManager()
    km_decrypt.set_key(list(key_bits))

    message = "Hello Bob!"
    ciphertext, enc_details = encrypt_message(message, km_encrypt)
    plaintext, dec_details = decrypt_message(ciphertext, km_decrypt)

    assert plaintext == message


def test_encrypt_different_key_fails():
    """Decrypting with wrong key should produce garbage."""
    from src.bb84.protocol import generate_random_bits

    km1 = KeyManager()
    km1.set_key(generate_random_bits(256))

    km2 = KeyManager()
    km2.set_key(generate_random_bits(256))

    ciphertext, _ = encrypt_message("Secret", km1)
    plaintext, _ = decrypt_message(ciphertext, km2)

    assert plaintext != "Secret"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
