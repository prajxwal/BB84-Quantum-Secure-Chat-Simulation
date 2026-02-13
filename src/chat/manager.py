"""
BB84 Quantum Chat - Chat Manager
Orchestrates the chat loop: commands, send/receive, encryption, BB84, and UI.
"""

import time
import threading
from datetime import datetime
from typing import Optional

from config.constants import (
    MSG_CHAT, MSG_BB84_INIT, MSG_BB84_PHOTONS, MSG_BB84_BASES,
    MSG_BB84_MATCHES, MSG_BB84_SAMPLE, MSG_BB84_VERIFY, MSG_BB84_COMPLETE,
    MSG_BB84_ABORT, MSG_EVE_TOGGLE, MSG_DISCONNECT, MSG_KEY_ROTATE,
)
from config.settings import NUM_PHOTONS, ERROR_THRESHOLD
from src.bb84.protocol import bb84_simulate
from src.bb84.eavesdropper import Eve
from src.crypto.encryption import encrypt_message, decrypt_message
from src.crypto.key_manager import KeyManager, KeyExhaustedError
from src.crypto.utils import key_to_hex
from src.chat.message import Message
from src.chat.history import ChatHistory
from src.stats.collector import Statistics
from src.ui.interface import (
    create_console, display_header, display_message, display_system_message,
    display_status_bar, display_key_info, display_welcome, display_chat_history,
)
from src.ui.bb84_view import display_bb84_exchange
from src.ui.encryption_view import display_encryption, display_decryption
from src.ui.stats_view import display_stats
from src.ui.help_view import display_help
from src.ui.eve_view import display_eve_analysis


class ChatManager:
    """Orchestrates the entire chat application."""

    def __init__(self, role: str, network):
        self.role = role                    # "Alice" or "Bob"
        self.peer = "Bob" if role == "Alice" else "Alice"
        self.network = network              # Server or Client instance
        self.console = create_console()
        self.key_manager = KeyManager()
        self.history = ChatHistory()
        self.stats = Statistics()
        self.eve = Eve()
        self.eve_active = False
        self.verbose = True
        self.running = True
        self._lock = threading.Lock()
        self.peer_address = ""

    # ─── BB84 Key Exchange ──────────────────────────────────────

    def perform_key_exchange(self, animate: bool = True):
        """Perform a BB84 key exchange (local simulation shared by both peers)."""
        display_system_message(self.console, "Initiating BB84 key exchange...", "INFO")
        start_time = time.time()

        result = bb84_simulate(
            num_photons=NUM_PHOTONS,
            eve_intercept=self.eve_active,
            eve_instance=self.eve if self.eve_active else None,
        )

        duration = time.time() - start_time

        # Show visualization
        display_bb84_exchange(self.console, result, animate=animate)

        if result.get('eve_active'):
            display_eve_analysis(self.console, result)

        if result['eavesdropper_detected']:
            self.stats.record_eve_detection()
            self.key_manager.mark_compromised()
            display_system_message(
                self.console,
                f"Eavesdropper detected! Error rate: {result['error_rate']:.1%}. Key discarded.",
                "ERROR"
            )
            display_system_message(self.console, "Establishing new secure channel...", "INFO")
            # Retry without Eve active for the fresh key
            self.eve_active = False
            self.stats.eve_active = False
            self.perform_key_exchange(animate=False)
            return

        if result['key_too_short']:
            display_system_message(
                self.console,
                f"Key too short ({result['final_key_length']} bits). Retrying...",
                "WARNING"
            )
            self.perform_key_exchange(animate=False)
            return

        # Set the new key
        key = self.key_manager.set_key(result['alice_final_key'], result['error_rate'])

        # Sync key with peer — send our key data so both sides have the same key
        # In a real quantum system the key is derived independently at each end.
        # For this simulation, we send the key over the classical channel after BB84.
        try:
            self.network.send(MSG_BB84_COMPLETE, {
                'key': result['alice_final_key'],
                'error_rate': result['error_rate'],
            })
        except Exception:
            pass  # peer will also have run its own simulation

        # Record stats
        self.stats.record_key_exchange(
            photons=NUM_PHOTONS,
            matches=len(result['matching_positions']),
            match_rate=result['match_rate'],
            error_rate=result['error_rate'],
            key_length=result['final_key_length'],
            duration=duration,
        )

        display_system_message(
            self.console,
            f"Secure key established: {key.length} bits (#{key.id})",
            "SUCCESS"
        )

    # ─── Message Handling ───────────────────────────────────────

    def send_chat_message(self, text: str):
        """Encrypt and send a chat message."""
        if not self.key_manager.get_key():
            display_system_message(self.console, "No key! Use /refresh first.", "ERROR")
            return

        # Check if key needs rotation
        key = self.key_manager.get_key()
        bits_needed = len(text) * 8
        if key.remaining() < bits_needed:
            display_system_message(self.console, "Key exhausted. Auto-rotating...", "WARNING")
            self.stats.record_auto_rotation()
            self.perform_key_exchange(animate=False)

        try:
            ciphertext, details = encrypt_message(text, self.key_manager)
        except KeyExhaustedError:
            display_system_message(self.console, "Key exhausted. Use /refresh.", "ERROR")
            return

        # Show encryption visualization if verbose
        if self.verbose:
            display_encryption(self.console, details, "SENDING")

        # Create message record
        msg = Message(sender=self.role, content=text, encrypted=ciphertext, bits_used=details['bits_used'])
        self.history.add_message(msg)

        # Send over network
        self.network.send(MSG_CHAT, {
            'sender': self.role,
            'ciphertext': ciphertext,
            'bits_used': details['bits_used'],
        })

        # Display
        display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_sent(len(text.encode('utf-8')))

        # Check rotation threshold
        key = self.key_manager.get_key()
        if key and key.needs_rotation():
            display_system_message(
                self.console,
                f"Key usage at {key.usage_percentage():.0f}%. Rotation recommended (/refresh).",
                "WARNING"
            )

    def handle_received_message(self, msg_type: int, payload: dict, seq: int):
        """Handle an incoming network message (called from receive thread)."""
        with self._lock:
            if msg_type == MSG_CHAT:
                self._handle_chat(payload)
            elif msg_type == MSG_BB84_COMPLETE:
                self._handle_key_sync(payload)
            elif msg_type == MSG_EVE_TOGGLE:
                eve_state = payload.get('active', False)
                self.eve_active = eve_state
                self.stats.eve_active = eve_state
                state_str = "enabled" if eve_state else "disabled"
                display_system_message(self.console, f"Peer toggled Eve: {state_str}", "INFO")
            elif msg_type == MSG_DISCONNECT:
                display_system_message(self.console, "Peer disconnected.", "WARNING")
                self.running = False
            elif msg_type == MSG_KEY_ROTATE:
                display_system_message(self.console, "Peer requested key refresh.", "INFO")
                self.perform_key_exchange(animate=True)

    def _handle_chat(self, payload: dict):
        """Handle incoming chat message."""
        ciphertext = payload['ciphertext']
        sender = payload.get('sender', self.peer)
        bits_used = payload.get('bits_used', 0)

        if not self.key_manager.get_key():
            display_system_message(self.console, "Received message but no key!", "ERROR")
            return

        try:
            plaintext, details = decrypt_message(ciphertext, self.key_manager)
        except KeyExhaustedError:
            display_system_message(self.console, "Key exhausted during decrypt!", "ERROR")
            return

        if self.verbose:
            display_decryption(self.console, details)

        msg = Message(sender=sender, content=plaintext, encrypted=ciphertext, bits_used=bits_used)
        self.history.add_message(msg)
        display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_received(len(plaintext.encode('utf-8')))

    def _handle_key_sync(self, payload: dict):
        """Handle key synchronization from peer."""
        key_bits = payload.get('key', [])
        error_rate = payload.get('error_rate', 0.0)
        if key_bits:
            self.key_manager.set_key(key_bits, error_rate)
            display_system_message(
                self.console,
                f"Key synchronized from peer: {len(key_bits)} bits",
                "SUCCESS"
            )

    # ─── Command Processing ────────────────────────────────────

    def process_command(self, cmd: str) -> bool:
        """
        Process a /command. Returns False if the app should quit.
        """
        parts = cmd.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == '/help':
            display_help(self.console)

        elif command == '/key':
            display_key_info(self.console, self.key_manager)

        elif command == '/refresh':
            self.stats.record_manual_rotation()
            try:
                self.network.send(MSG_KEY_ROTATE, {})
            except Exception:
                pass
            self.perform_key_exchange(animate=True)

        elif command == '/stats':
            display_stats(self.console, self.stats, self.key_manager,
                          self.role, self.peer_address)

        elif command == '/eve':
            if args and args[0].lower() == 'on':
                self.eve_active = True
                self.stats.eve_active = True
                display_system_message(self.console, "Eavesdropper simulation enabled.", "WARNING")
                display_system_message(self.console, "Eve will intercept next key exchange.", "WARNING")
                try:
                    self.network.send(MSG_EVE_TOGGLE, {'active': True})
                except Exception:
                    pass
            elif args and args[0].lower() == 'off':
                self.eve_active = False
                self.stats.eve_active = False
                display_system_message(self.console, "Eavesdropper simulation disabled.", "SUCCESS")
                try:
                    self.network.send(MSG_EVE_TOGGLE, {'active': False})
                except Exception:
                    pass
            else:
                state = "ON" if self.eve_active else "OFF"
                display_system_message(self.console, f"Eve is currently {state}. Use /eve on or /eve off.", "INFO")

        elif command == '/verbose':
            if args and args[0].lower() == 'on':
                self.verbose = True
                display_system_message(self.console, "Verbose mode enabled.", "INFO")
            elif args and args[0].lower() == 'off':
                self.verbose = False
                display_system_message(self.console, "Verbose mode disabled.", "INFO")
            else:
                state = "ON" if self.verbose else "OFF"
                display_system_message(self.console, f"Verbose is {state}. Use /verbose on or /verbose off.", "INFO")

        elif command == '/clear':
            self.console.clear()
            display_header(self.console, self.role, self.peer, self.key_manager, self.stats)

        elif command == '/history':
            display_chat_history(self.console, self.history, show_encrypted=True)

        elif command == '/export':
            filename = f"chat_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.history.export(filename)
            display_system_message(self.console, f"Transcript exported to {filename}", "SUCCESS")

        elif command == '/quit':
            display_system_message(self.console, "Disconnecting...", "INFO")
            try:
                self.network.send(MSG_DISCONNECT, {})
            except Exception:
                pass
            self.running = False
            return False

        else:
            display_system_message(self.console, f"Unknown command: {command}. Type /help.", "ERROR")

        return True

    # ─── Main Chat Loop ────────────────────────────────────────

    def run(self):
        """Main chat loop — read input and dispatch."""
        display_welcome(self.console, self.role)
        self.stats.mark_connected()

        # Perform initial key exchange
        self.perform_key_exchange(animate=True)

        # Start receiving thread
        self.network.start_receiving(self.handle_received_message)

        # Display header and status
        display_header(self.console, self.role, self.peer, self.key_manager, self.stats)
        display_status_bar(self.console, self.key_manager, self.stats)

        # Chat loop
        while self.running:
            try:
                user_input = input(f"\n  {self.role} > ").strip()
                if not user_input:
                    continue

                if user_input.startswith('/'):
                    if not self.process_command(user_input):
                        break
                else:
                    self.send_chat_message(user_input)

            except (KeyboardInterrupt, EOFError):
                self.console.print()
                display_system_message(self.console, "Disconnecting...", "INFO")
                try:
                    self.network.send(MSG_DISCONNECT, {})
                except Exception:
                    pass
                break

        self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.key_manager.clear()
        self.network.stop()
        display_system_message(self.console, "Keys cleared from memory. Goodbye!", "SUCCESS")
