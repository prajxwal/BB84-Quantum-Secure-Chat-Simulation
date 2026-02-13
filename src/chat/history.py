"""
BB84 Quantum Chat - Chat History
Stores and manages message history.
"""

import json
from datetime import datetime
from typing import List, Optional

from src.chat.message import Message


class ChatHistory:
    """Manages a list of chat messages."""

    def __init__(self):
        self.messages: List[Message] = []
        self.system_messages: List[dict] = []

    def add_message(self, message: Message):
        """Add a chat message."""
        self.messages.append(message)

    def add_system(self, text: str, level: str = 'INFO'):
        """Add a system/info message."""
        self.system_messages.append({
            'text': text,
            'level': level,
            'timestamp': datetime.now(),
        })

    def get_all(self) -> List[Message]:
        return list(self.messages)

    def get_recent(self, n: int = 50) -> List[Message]:
        return self.messages[-n:]

    def clear_display(self):
        """Clear the display buffer but keep the internal log."""
        pass  # messages are preserved; UI clears its view

    def count(self) -> int:
        return len(self.messages)

    def count_by_sender(self, sender: str) -> int:
        return sum(1 for m in self.messages if m.sender == sender)

    def total_data(self) -> int:
        """Total data in bytes (content length)."""
        return sum(len(m.content.encode('utf-8')) for m in self.messages)

    def export(self, filepath: str):
        """Export chat transcript to a text file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"BB84 Quantum Chat Transcript\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total messages: {self.count()}\n")
            f.write("=" * 60 + "\n\n")
            for msg in self.messages:
                f.write(f"[{msg.time_str()}] {msg.sender}: {msg.content}\n")
                if msg.encrypted:
                    f.write(f"           [ENCRYPTED] {msg.encrypted}\n")
                f.write("\n")
            f.write("=" * 60 + "\n")
            f.write(f"Total data: {self.total_data()} bytes\n")
