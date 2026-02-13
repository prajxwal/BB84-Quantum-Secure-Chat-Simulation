"""
BB84 Quantum Chat - TCP Client (Alice's side)
"""

import socket
import time
import threading
from typing import Optional, Callable, Any

from config.settings import HOST, PORT, BUFFER_SIZE, CONNECTION_TIMEOUT, RETRY_ATTEMPTS, RETRY_BACKOFF
from src.network.protocol import send_message, recv_message, ProtocolError


class Client:
    """TCP client for Alice — connects to Bob's server."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._on_message: Optional[Callable] = None

    def connect(self, retries: int = RETRY_ATTEMPTS) -> bool:
        """
        Connect to the server with exponential backoff retry.
        Returns True if connected, False otherwise.
        """
        for attempt in range(retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(CONNECTION_TIMEOUT)
                self.socket.connect((self.host, self.port))
                self.running = True
                return True
            except (ConnectionRefusedError, socket.timeout, OSError):
                if attempt < retries - 1:
                    backoff = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    time.sleep(backoff)
                else:
                    return False
        return False

    def send(self, msg_type: int, payload: Any):
        """Send a message to the server."""
        if self.socket:
            send_message(self.socket, msg_type, payload)

    def receive(self):
        """Receive a message from the server."""
        if self.socket:
            return recv_message(self.socket)
        return None

    def start_receiving(self, on_message: Callable):
        """Start background thread for receiving messages."""
        self._on_message = on_message
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._recv_thread.start()

    def _receive_loop(self):
        """Background receive loop."""
        while self.running and self.socket:
            try:
                msg_type, payload, seq = recv_message(self.socket)
                if self._on_message:
                    self._on_message(msg_type, payload, seq)
            except (ProtocolError, ConnectionError, OSError):
                if self.running:
                    self.running = False
                break
            except Exception:
                if self.running:
                    self.running = False
                break

    def stop(self):
        """Gracefully close the connection."""
        self.running = False
        try:
            if self.socket:
                self.socket.close()
        except Exception:
            pass
