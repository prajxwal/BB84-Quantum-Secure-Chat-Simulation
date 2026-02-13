"""
BB84 Quantum Chat - Message Model
"""

import uuid
from datetime import datetime


class Message:
    """Represents a single chat message."""

    def __init__(self, sender: str, content: str, encrypted: str = '', bits_used: int = 0):
        self.id = str(uuid.uuid4())[:8]
        self.sender = sender
        self.content = content          # plaintext
        self.encrypted = encrypted      # ciphertext hex
        self.timestamp = datetime.now()
        self.bits_used = bits_used

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'sender': self.sender,
            'content': self.content,
            'encrypted': self.encrypted,
            'timestamp': self.timestamp.isoformat(),
            'bits_used': self.bits_used,
        }

    def time_str(self) -> str:
        return self.timestamp.strftime('%H:%M:%S')

    def __repr__(self) -> str:
        return f"Message({self.sender}: {self.content[:30]}...)"
