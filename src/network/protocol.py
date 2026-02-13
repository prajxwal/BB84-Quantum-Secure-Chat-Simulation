"""
BB84 Quantum Chat - Network Protocol
Packet framing for TCP communication: type byte + 4-byte length + JSON payload.
"""

import json
import struct
import zlib
from typing import Tuple, Any


HEADER_FORMAT = '!BIi'  # type(1B) + length(4B) + sequence(4B)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


class ProtocolError(Exception):
    """Raised on network protocol violations."""
    pass


_sequence_counter = 0


def _next_sequence() -> int:
    global _sequence_counter
    _sequence_counter += 1
    return _sequence_counter


def pack_message(msg_type: int, payload: Any, seq: int = None) -> bytes:
    """
    Pack a message for transmission.

    Format: [type:1B][payload_len:4B][seq:4B][payload:variable]
    """
    if seq is None:
        seq = _next_sequence()

    payload_bytes = json.dumps(payload).encode('utf-8')
    header = struct.pack(HEADER_FORMAT, msg_type, len(payload_bytes), seq)
    return header + payload_bytes


def unpack_header(data: bytes) -> Tuple[int, int, int]:
    """Unpack just the header to get type, payload length, and sequence."""
    if len(data) < HEADER_SIZE:
        raise ProtocolError(f"Header too short: {len(data)} < {HEADER_SIZE}")
    msg_type, payload_len, seq = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    return msg_type, payload_len, seq


def unpack_payload(data: bytes) -> Any:
    """Unpack payload bytes as JSON."""
    return json.loads(data.decode('utf-8'))


def recv_message(sock) -> Tuple[int, Any, int]:
    """
    Receive a complete message from a socket.

    Returns: (msg_type, payload_dict, sequence_number)
    """
    # Read header
    header_data = _recv_exactly(sock, HEADER_SIZE)
    if not header_data:
        raise ProtocolError("Connection closed")

    msg_type, payload_len, seq = unpack_header(header_data)

    # Read payload
    if payload_len > 0:
        payload_data = _recv_exactly(sock, payload_len)
        if not payload_data:
            raise ProtocolError("Connection closed during payload read")
        payload = unpack_payload(payload_data)
    else:
        payload = {}

    return msg_type, payload, seq


def send_message(sock, msg_type: int, payload: Any):
    """Send a complete message over a socket."""
    data = pack_message(msg_type, payload)
    sock.sendall(data)


def _recv_exactly(sock, num_bytes: int) -> bytes:
    """Receive exactly num_bytes from a socket."""
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk:
            return None
        data += chunk
    return data
