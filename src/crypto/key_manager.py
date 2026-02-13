"""
BB84 Quantum Chat - Key Manager
Manages encryption keys: storage, usage tracking, rotation.
Keys are NEVER written to disk.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from config.settings import KEY_ROTATION_THRESHOLD, MAX_KEY_LENGTH


class KeyExhaustedError(Exception):
    """Raised when there are insufficient key bits remaining."""
    pass


class EncryptionKey:
    """Represents a single BB84-generated encryption key."""

    def __init__(self, key_bits: List[int], error_rate: float = 0.0):
        self.id = str(uuid.uuid4())[:8]
        self.bits = key_bits[:MAX_KEY_LENGTH]
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
