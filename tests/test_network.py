"""
Tests for Network Protocol
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.network.protocol import pack_message, unpack_header, unpack_payload, HEADER_SIZE
from config.constants import MSG_CHAT, MSG_BB84_INIT


def test_pack_unpack_header():
    """Pack and unpack should preserve message type and length."""
    payload = {'message': 'hello'}
    data = pack_message(MSG_CHAT, payload, seq=42)

    msg_type, payload_len, seq = unpack_header(data)
    assert msg_type == MSG_CHAT
    assert seq == 42
    assert payload_len > 0


def test_pack_unpack_payload():
    """Payload should round-trip through pack/unpack."""
    payload = {'key': [1, 0, 1], 'rate': 0.05}
    data = pack_message(MSG_BB84_INIT, payload, seq=1)

    msg_type, payload_len, seq = unpack_header(data)
    result = unpack_payload(data[HEADER_SIZE:HEADER_SIZE + payload_len])

    assert result['key'] == [1, 0, 1]
    assert result['rate'] == 0.05


def test_empty_payload():
    """Empty payload should work."""
    data = pack_message(MSG_CHAT, {}, seq=1)
    msg_type, payload_len, seq = unpack_header(data)
    assert msg_type == MSG_CHAT
    result = unpack_payload(data[HEADER_SIZE:HEADER_SIZE + payload_len])
    assert result == {}


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
