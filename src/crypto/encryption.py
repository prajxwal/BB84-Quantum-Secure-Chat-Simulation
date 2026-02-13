"""
BB84 Quantum Chat - XOR Encryption Engine
Encrypts/decrypts messages using the BB84-generated key via XOR.
"""

from typing import List, Tuple

from src.crypto.utils import text_to_binary, binary_to_text, binary_to_hex, hex_to_binary
from src.crypto.key_manager import KeyManager, KeyExhaustedError


def xor_bits(data_bits: List[int], key_bits: List[int]) -> List[int]:
    """XOR two bit lists together."""
    return [d ^ k for d, k in zip(data_bits, key_bits)]


def encrypt_message(
    message: str,
    key_manager: KeyManager,
) -> Tuple[str, dict]:
    """
    Encrypt a message using the BB84 key via XOR.

    Returns:
        - ciphertext_hex: hexadecimal ciphertext
        - details: dict with visualization data (message_bits, key_bits, cipher_bits)
    """
    message_bits = text_to_binary(message)
    num_bits = len(message_bits)

    key_bits = key_manager.consume_bits(num_bits)
    cipher_bits = xor_bits(message_bits, key_bits)
    ciphertext_hex = binary_to_hex(cipher_bits)

    details = {
        'message': message,
        'message_bits': message_bits,
        'key_bits': key_bits,
        'cipher_bits': cipher_bits,
        'ciphertext_hex': ciphertext_hex,
        'bits_used': num_bits,
    }

    return ciphertext_hex, details


def decrypt_message(
    ciphertext_hex: str,
    key_manager: KeyManager,
) -> Tuple[str, dict]:
    """
    Decrypt a hexadecimal ciphertext using the BB84 key via XOR.

    Returns:
        - plaintext: decrypted message string
        - details: dict with visualization data
    """
    cipher_bits = hex_to_binary(ciphertext_hex)
    num_bits = len(cipher_bits)

    key_bits = key_manager.consume_bits(num_bits)
    message_bits = xor_bits(cipher_bits, key_bits)
    plaintext = binary_to_text(message_bits)

    details = {
        'ciphertext_hex': ciphertext_hex,
        'cipher_bits': cipher_bits,
        'key_bits': key_bits,
        'message_bits': message_bits,
        'plaintext': plaintext,
        'bits_used': num_bits,
    }

    return plaintext, details
