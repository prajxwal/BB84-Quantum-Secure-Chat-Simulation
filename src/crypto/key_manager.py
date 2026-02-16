"""
BB84 Quantum Chat - Key Manager
Manages encryption keys: storage, usage tracking, rotation.
Keys are NEVER written to disk.
"""

import hashlib
import hmac
import uuid
from datetime import datetime
from typing import List, Optional

from config.settings import KEY_ROTATION_THRESHOLD, MAX_KEY_LENGTH

# Expanded key length in bits — derived from the short BB84 seed
EXPANDED_KEY_BITS = 1024


class KeyExhaustedError(Exception):
    """Raised when there are insufficient key bits remaining."""
    pass


def expand_key_bits(seed_bits: List[int], length: int = EXPANDED_KEY_BITS) -> List[int]:
    """
    Expand a short BB84 key into a longer keystream using HMAC-SHA256
    (similar to HKDF-Expand). The quantum-derived bits provide the entropy;
    this function stretches them into a usable keystream.
    """
    # Convert seed bits to bytes
    seed_str = ''.join(str(b) for b in seed_bits)
    seed_bytes = hashlib.sha256(seed_str.encode()).digest()

    expanded = []
    counter = 0
    prev = b''
    while len(expanded) < length:
        block = hmac.new(
            seed_bytes,
            prev + counter.to_bytes(4, 'big'),
            hashlib.sha256,
        ).digest()
        prev = block
        for byte in block:
            for i in range(7, -1, -1):
                expanded.append((byte >> i) & 1)
                if len(expanded) >= length:
                    break
            if len(expanded) >= length:
                break
        counter += 1
    return expanded[:length]


class EncryptionKey:
    """Represents a single BB84-generated encryption key."""

    def __init__(self, key_bits: List[int], error_rate: float = 0.0):
        self.id = str(uuid.uuid4())[:8]
        self.seed_bits = list(key_bits)          # original BB84 bits (for display)
        self.seed_length = len(self.seed_bits)
        # Expand the short quantum key into a usable keystream
        self.bits = expand_key_bits(key_bits, EXPANDED_KEY_BITS)
        self.length = len(self.bits)
        self.generated_at = datetime.now()
        self.bits_used = 0
        self.error_rate = error_rate

    def consume(self, num_bits: int) -> List[int]:
        """Consume bits from the key for encryption/decryption."""
        if self.bits_used + num_bits > self.length:
            raise KeyExhaustedError(
                f"Need {num_bits} bits but only {self.remaining()} remain"
            )
        consumed = self.bits[self.bits_used:self.bits_used + num_bits]
        self.bits_used += num_bits
        return consumed

    def remaining(self) -> int:
        return self.length - self.bits_used

    def usage_percentage(self) -> float:
        if self.length == 0:
            return 100.0
        return (self.bits_used / self.length) * 100.0

    def needs_rotation(self) -> bool:
        return self.usage_percentage() >= (KEY_ROTATION_THRESHOLD * 100)

    def age_seconds(self) -> float:
        return (datetime.now() - self.generated_at).total_seconds()

    def __repr__(self) -> str:
        return (
            f"EncryptionKey(id={self.id}, length={self.length}, "
            f"used={self.bits_used}, remaining={self.remaining()})"
        )


class KeyManager:
    """Manages encryption key lifecycle."""

    def __init__(self):
        self.current_key: Optional[EncryptionKey] = None
        self.key_history: List[dict] = []
        self.keys_generated = 0
        self.keys_compromised = 0

    def set_key(self, key_bits: List[int], error_rate: float = 0.0) -> EncryptionKey:
        """Set a new current encryption key."""
        if self.current_key:
            self.key_history.append({
                'id': self.current_key.id,
                'length': self.current_key.length,
                'bits_used': self.current_key.bits_used,
                'generated_at': self.current_key.generated_at.isoformat(),
                'error_rate': self.current_key.error_rate,
            })
        self.current_key = EncryptionKey(key_bits, error_rate)
        self.keys_generated += 1
        return self.current_key

    def get_key(self) -> Optional[EncryptionKey]:
        return self.current_key

    def consume_bits(self, num_bits: int) -> List[int]:
        """Consume bits from the current key."""
        if not self.current_key:
            raise KeyExhaustedError("No key available")
        return self.current_key.consume(num_bits)

    def needs_rotation(self) -> bool:
        if not self.current_key:
            return True
        return self.current_key.needs_rotation()

    def mark_compromised(self):
        """Mark current key as compromised."""
        self.keys_compromised += 1
        self.current_key = None

    def clear(self):
        """Securely clear the current key from memory."""
        if self.current_key:
            self.current_key.bits = [0] * len(self.current_key.bits)
            self.current_key = None
