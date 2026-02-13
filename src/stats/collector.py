"""
BB84 Quantum Chat - Statistics Collector
Tracks all application metrics.
"""

from datetime import datetime, timedelta
from typing import Optional


class Statistics:
    """Collects and calculates all application statistics."""

    def __init__(self):
        # Connection
        self.connected_at: Optional[datetime] = None
        self.reconnection_count = 0
        self.last_activity = datetime.now()

        # Messages
        self.messages_sent = 0
        self.messages_received = 0
        self.data_encrypted = 0     # bytes
        self.data_decrypted = 0     # bytes

        # Keys
        self.keys_generated = 0
        self.keys_compromised = 0
        self.auto_rotations = 0
        self.manual_rotations = 0

        # BB84
        self.total_photons_sent = 0
        self.total_basis_matches = 0
        self.last_match_rate = 0.0
        self.last_error_rate = 0.0
        self.last_key_length = 0
        self.last_exchange_duration = 0.0
        self.exchange_count = 0
        self.exchange_match_rates = []
        self.exchange_error_rates = []
        self.exchange_durations = []

        # Security
        self.eavesdropper_detected_count = 0
        self.eve_active = False
        self.last_security_check = datetime.now()

    def mark_connected(self):
        self.connected_at = datetime.now()
        self.last_activity = datetime.now()

    def record_message_sent(self, data_bytes: int):
        self.messages_sent += 1
        self.data_encrypted += data_bytes
        self.last_activity = datetime.now()

    def record_message_received(self, data_bytes: int):
        self.messages_received += 1
        self.data_decrypted += data_bytes
        self.last_activity = datetime.now()

    def record_key_exchange(self, photons: int, matches: int, match_rate: float,
                            error_rate: float, key_length: int, duration: float):
        self.keys_generated += 1
        self.exchange_count += 1
        self.total_photons_sent += photons
        self.total_basis_matches += matches
        self.last_match_rate = match_rate
        self.last_error_rate = error_rate
        self.last_key_length = key_length
        self.last_exchange_duration = duration
        self.exchange_match_rates.append(match_rate)
        self.exchange_error_rates.append(error_rate)
        self.exchange_durations.append(duration)
        self.last_security_check = datetime.now()
        self.last_activity = datetime.now()

    def record_eve_detection(self):
        self.eavesdropper_detected_count += 1
        self.keys_compromised += 1

    def record_auto_rotation(self):
        self.auto_rotations += 1

    def record_manual_rotation(self):
        self.manual_rotations += 1

    def uptime(self) -> timedelta:
        if self.connected_at:
            return datetime.now() - self.connected_at
        return timedelta(0)

    def uptime_str(self) -> str:
        td = self.uptime()
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def avg_match_rate(self) -> float:
        if not self.exchange_match_rates:
            return 0.0
        return sum(self.exchange_match_rates) / len(self.exchange_match_rates)

    def avg_error_rate(self) -> float:
        if not self.exchange_error_rates:
            return 0.0
        return sum(self.exchange_error_rates) / len(self.exchange_error_rates)

    def avg_duration(self) -> float:
        if not self.exchange_durations:
            return 0.0
        return sum(self.exchange_durations) / len(self.exchange_durations)

    def total_messages(self) -> int:
        return self.messages_sent + self.messages_received

    def total_data(self) -> int:
        return self.data_encrypted + self.data_decrypted

    def total_data_str(self) -> str:
        total = self.total_data()
        if total < 1024:
            return f"{total} B"
        elif total < 1024 * 1024:
            return f"{total / 1024:.1f} KB"
        return f"{total / (1024 * 1024):.1f} MB"

    def security_status(self) -> str:
        if self.eavesdropper_detected_count > 0 and self.last_error_rate > 0.10:
            return "COMPROMISED"
        if self.eve_active:
            return "EVE ACTIVE"
        return "SECURE"
