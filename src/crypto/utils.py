"""
BB84 Quantum Chat - Binary/Hex Conversion Utilities
"""

from typing import List


def text_to_binary(text: str) -> List[int]:
    """Convert a text string to a list of binary bits (8 bits per char)."""
    bits = []
    for char in text:
        char_bits = format(ord(char), '08b')
        bits.extend(int(b) for b in char_bits)
    return bits


def binary_to_text(bits: List[int]) -> str:
    """Convert a list of binary bits back to a text string."""
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i + 8]
        if len(byte) < 8:
            break
        char_value = int(''.join(str(b) for b in byte), 2)
        chars.append(chr(char_value))
    return ''.join(chars)


def binary_to_hex(bits: List[int]) -> str:
    """Convert a list of binary bits to a hexadecimal string."""
    hex_str = ''
    for i in range(0, len(bits), 4):
        nibble = bits[i:i + 4]
        if len(nibble) < 4:
            nibble.extend([0] * (4 - len(nibble)))
        value = int(''.join(str(b) for b in nibble), 2)
        hex_str += format(value, 'x')
    return hex_str


def hex_to_binary(hex_str: str) -> List[int]:
    """Convert a hexadecimal string to a list of binary bits."""
    bits = []
    for ch in hex_str:
        value = int(ch, 16)
        nibble = format(value, '04b')
        bits.extend(int(b) for b in nibble)
    return bits


def bits_to_string(bits: List[int]) -> str:
    """Convert bit list to a displayable binary string grouped by bytes."""
    s = ''.join(str(b) for b in bits)
    return ' '.join(s[i:i + 8] for i in range(0, len(s), 8))


def key_to_hex(bits: List[int]) -> str:
    """Convert key bits to hex display string."""
    return binary_to_hex(bits)
