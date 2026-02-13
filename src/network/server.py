"""
BB84 Quantum Chat - TCP Server (Bob's side)
"""

import socket
import threading
from typing import Optional, Callable, Any

from config.settings import HOST, PORT, BUFFER_SIZE, CONNECTION_TIMEOUT
from src.network.protocol import send_message, recv_message, ProtocolError


class Server:
    """TCP server for Bob — accepts one client connection."""

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.client_socket: Optional[socket.socket] = None
        self.client_address = None
        self.running = False
        self._recv_thread: Optional[threading.Thread] = None
        self._on_message: Optional[Callable] = None

    def start(self):
        """Create and bind the server socket."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        self.running = True

    def accept_connection(self) -> tuple:
        """Wait for and accept a client connection."""
        self.client_socket, self.client_address = self.server_socket.accept()
        self.client_socket.settimeout(CONNECTION_TIMEOUT)
        return self.client_address

    def send(self, msg_type: int, payload: Any):
        """Send a message to the connected client."""
        if self.client_socket:
            send_message(self.client_socket, msg_type, payload)

    def receive(self):
        """Receive a message from the connected client."""
        if self.client_socket:
            return recv_message(self.client_socket)
        return None

    def start_receiving(self, on_message: Callable):
        """Start background thread for receiving messages."""
        self._on_message = on_message
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._recv_thread.start()

    def _receive_loop(self):
        """Background receive loop."""
        while self.running and self.client_socket:
            try:
                msg_type, payload, seq = recv_message(self.client_socket)
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
        """Gracefully shut down the server."""
        self.running = False
        try:
            if self.client_socket:
                self.client_socket.close()
        except Exception:
            pass
        try:
            if self.server_socket:
                self.server_socket.close()
        except Exception:
            pass
