"""
BB84 Quantum Chat - Chat Manager
Orchestrates the chat loop: interactive BB84 key exchange, commands, send/receive, encryption.
"""

import time
import threading
from datetime import datetime
from typing import Optional, List

from config.constants import (
    MSG_CHAT, MSG_BB84_INIT, MSG_BB84_PHOTONS, MSG_BB84_BASES,
    MSG_BB84_MATCHES, MSG_BB84_SAMPLE, MSG_BB84_VERIFY, MSG_BB84_COMPLETE,
    MSG_BB84_ABORT, MSG_EVE_TOGGLE, MSG_DISCONNECT, MSG_KEY_ROTATE,
    RECTILINEAR, DIAGONAL, ANGLES, INTERACTIVE_SYMBOLS, BIT_BASIS_TO_SYMBOL,
    ANGLE_SYMBOLS,
)
from config.settings import INTERACTIVE_NUM_PHOTONS, ERROR_THRESHOLD, SAMPLE_FRACTION
from src.bb84.protocol import (
    encode_photon, encode_photons, measure_photon, measure_photons,
    find_matching_positions, extract_key_bits, check_errors, remove_sample_bits,
    generate_random_bits, generate_random_bases,
)
from src.bb84.photon import Photon
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
from src.ui.bb84_view import display_bb84_interactive_result
from src.ui.encryption_view import display_encryption, display_decryption
from src.ui.stats_view import display_stats
from src.ui.help_view import display_help


class ChatManager:
    """Orchestrates the entire chat application."""

    def __init__(self, role: str, network):
        self.role = role                    # "Alice" or "Bob"
        self.peer = "Bob" if role == "Alice" else "Alice"
        self.network = network              # Server or Client instance
        self.console = create_console()
        # Separate key managers for send and receive to keep cursors in sync
        self.send_key_manager = KeyManager()
        self.recv_key_manager = KeyManager()
        self.history = ChatHistory()
        self.stats = Statistics()
        self.verbose = False
        self.running = True
        self._lock = threading.Lock()
        self.peer_address = ""

        # Synchronization events for interactive BB84
        self._key_ready = threading.Event()
        self._init_received = threading.Event()     # Alice signals she's starting
        self._photons_received = threading.Event()
        self._bases_received = threading.Event()
        self._matches_received = threading.Event()

        # Shared data for interactive exchange (set by receive thread)
        self._received_photons_data = None
        self._received_bases = None
        self._received_matches = None
        self._received_key = None
        self._received_error_rate = None

    # ─── Interactive BB84 Key Exchange ───────────────────────────

    def interactive_key_exchange_alice(self):
        """
        Alice's side of the interactive BB84 key exchange.
        Alice enters bits and bases manually, sends photons to Bob,
        waits for Bob's bases, then reconciles and sends the final key.
        """
        num = INTERACTIVE_NUM_PHOTONS
        self._clear_exchange_state()

        # Signal Bob that we're starting so he can begin waiting
        try:
            self.network.send(MSG_BB84_INIT, {'num_photons': num})
        except Exception:
            pass

        self.console.print()
        self.console.print("[bold bright_cyan]═══ BB84 Interactive Key Exchange ═══[/]")
        self.console.print(f"[dim]You will prepare {num} photons for Bob.[/dim]")
        self.console.print()

        # Step 1: Alice enters bits
        self.console.print("[bold bright_cyan]\\[1/7][/] Enter your random bits (0 or 1, space-separated):")
        self.console.print(f"[dim]  Need {num} bits. Example: 1 0 1 1 0 0 1 0 1 1 0 0 1 0 1 0[/dim]")
        alice_bits = self._prompt_bits(num)
        if alice_bits is None:
            return

        # Step 2: Alice enters bases
        self.console.print()
        self.console.print("[bold bright_cyan]\\[2/7][/] Enter your bases for each bit:")
        self.console.print("  [dim]Use polarization symbols:[/dim]  [bold]-[/]  [bold]|[/]  [bold]/[/]  [bold]\\\\[/]")
        self.console.print("  [dim]- and | are rectilinear,  / and \\\\ are diagonal[/dim]")
        self.console.print(f"  [dim]Need {num} symbols. Example: - | / \\\\ | - / \\\\ - | / \\\\ | - / \\\\[/dim]")
        alice_bases_input = self._prompt_bases(num)
        if alice_bases_input is None:
            return

        # Parse bases
        alice_bases = []
        for sym in alice_bases_input:
            if sym in ('-', '|'):
                alice_bases.append(RECTILINEAR)
            else:  # '/' or '\'
                alice_bases.append(DIAGONAL)

        # Step 3: Encode photons
        self.console.print()
        self.console.print("[bold bright_cyan]\\[3/7][/] Encoding photons...")
        photons = encode_photons(alice_bits, alice_bases)

        # Display what Alice prepared
        pol_list = []
        for p in photons:
            sym = BIT_BASIS_TO_SYMBOL.get((p.bit, p.basis), '?')
            pol_list.append(sym)
        polarizations = ' '.join(pol_list)
        self.console.print(f"  [dim]Your photons:[/dim] [bright_yellow]{polarizations}[/]")

        # Step 4: Send photons to Bob
        self.console.print()
        self.console.print("[bold bright_cyan]\\[4/7][/] Transmitting photons to Bob...")
        self.console.print("  Alice [bright_yellow]~~~> ~~~> ~~~> ~~~>[/] Bob")

        photon_data = [p.to_dict() for p in photons]
        try:
            self.network.send(MSG_BB84_PHOTONS, {'photons': photon_data})
        except Exception as e:
            display_system_message(self.console, f"Failed to send photons: {e}", "ERROR")
            return

        # Step 5: Wait for Bob's bases
        self.console.print()
        self.console.print("[bold bright_cyan]\\[5/7][/] Waiting for Bob to measure photons...")
        got_bases = self._bases_received.wait(timeout=300.0)
        if not got_bases:
            display_system_message(self.console, "Timed out waiting for Bob's bases.", "ERROR")
            return

        bob_bases = self._received_bases
        bob_bases_symbols = ' '.join(
            '+' if b == RECTILINEAR else '×' for b in bob_bases
        )
        self.console.print(f"  [dim]Bob's bases:[/dim] [bright_magenta]{bob_bases_symbols}[/]")

        # Step 6: Reconciliation
        self.console.print()
        self.console.print("[bold bright_cyan]\\[6/7][/] Basis reconciliation...")
        matching_positions = find_matching_positions(alice_bases, bob_bases)
        match_rate = len(matching_positions) / num

        # Display match/mismatch table
        self._display_basis_comparison(alice_bases, bob_bases, num)

        match_preview = ', '.join(str(p + 1) for p in matching_positions[:10])
        if len(matching_positions) > 10:
            match_preview += '...'
        self.console.print(f"  [dim]Matching positions:[/dim] [green]{match_preview}[/]")
        self.console.print(f"  [dim]Match rate:[/dim] {match_rate:.1%} ({len(matching_positions)}/{num})")

        # Send matching positions to Bob
        self.network.send(MSG_BB84_MATCHES, {
            'positions': matching_positions,
            'alice_bases': alice_bases,
        })

        # Extract raw keys
        alice_raw_key = extract_key_bits(alice_bits, matching_positions)

        # Step 7: Error checking
        self.console.print()
        self.console.print("[bold bright_cyan]\\[7/7][/] Error checking...")

        error_rate, sample_positions, alice_sample, bob_sample = check_errors(
            alice_raw_key, alice_raw_key
        )

        alice_final_key = remove_sample_bits(alice_raw_key, sample_positions)

        if len(alice_final_key) < 1:
            display_system_message(self.console, "Key too short! Try again with /refresh.", "ERROR")
            return

        # Set key on both send and receive managers
        self.send_key_manager.set_key(list(alice_final_key), 0.0)
        self.recv_key_manager.set_key(list(alice_final_key), 0.0)
        self._key_ready.set()

        # Send the key to Bob
        try:
            self.network.send(MSG_BB84_COMPLETE, {
                'key': alice_final_key,
                'error_rate': 0.0,
            })
        except Exception:
            pass

        # Display result
        display_bb84_interactive_result(self.console, alice_final_key, 0.0, match_rate, num)

        self.stats.record_key_exchange(
            photons=num, matches=len(matching_positions),
            match_rate=match_rate, error_rate=0.0,
            key_length=len(alice_final_key), duration=0.0,
        )

    def interactive_key_exchange_bob(self):
        """
        Bob's side of the interactive BB84 key exchange.
        Bob waits for init signal, then photons, enters his measurement bases,
        measures, sends bases back, waits for the final key.
        """
        num = INTERACTIVE_NUM_PHOTONS
        self._clear_exchange_state()

        self.console.print()
        self.console.print("[bold bright_cyan]═══ BB84 Interactive Key Exchange ═══[/]")
        self.console.print("[dim]Waiting for Alice to prepare photons...[/dim]")
        self.console.print("[dim](Alice is entering her bits and bases)[/dim]")
        self.console.print()

        # Wait for photons from Alice (long timeout since Alice is typing manually)
        got_photons = self._photons_received.wait(timeout=600.0)
        if not got_photons:
            display_system_message(self.console, "Timed out waiting for Alice's photons.", "ERROR")
            return

        photon_data = self._received_photons_data
        photons = [Photon.from_dict(d) for d in photon_data]
        num = len(photons)

        self.console.print(f"[bold bright_cyan]\\[4/7][/] Received {num} photons from Alice!")
        self.console.print("  Alice [bright_yellow]~~~> ~~~> ~~~> ~~~>[/] Bob")
        self.console.print()

        # Bob chooses measurement bases
        self.console.print("[bold bright_cyan]\\[5/7][/] Choose your measurement bases:")
        self.console.print("  [dim]Use polarization symbols:[/dim]  [bold]-[/]  [bold]|[/]  [bold]/[/]  [bold]\\\\[/]")
        self.console.print("  [dim]- and | are rectilinear,  / and \\\\ are diagonal[/dim]")
        self.console.print(f"  [dim]Need {num} symbols. Example: | - \\\\ / - | \\\\ / | - \\\\ / - | \\\\ /[/dim]")
        bob_bases_input = self._prompt_bases(num)
        if bob_bases_input is None:
            return

        bob_bases = []
        for sym in bob_bases_input:
            if sym in ('-', '|'):
                bob_bases.append(RECTILINEAR)
            else:
                bob_bases.append(DIAGONAL)

        # Measure photons
        bob_bits = measure_photons(photons, bob_bases)

        # Display what Bob measured
        measured_list = []
        for b, ba in zip(bob_bits, bob_bases):
            sym = BIT_BASIS_TO_SYMBOL.get((b, ba), '?')
            measured_list.append(sym)
        measured_symbols = ' '.join(measured_list)
        self.console.print(f"  [dim]Your measurements:[/dim] [bright_yellow]{measured_symbols}[/]")
        self.console.print(f"  [dim]Measured bits:[/dim] {' '.join(str(b) for b in bob_bits)}")

        # Send bases to Alice
        self.console.print()
        self.console.print("[dim]Sending your bases to Alice...[/dim]")
        self.network.send(MSG_BB84_BASES, {'bases': bob_bases})

        # Wait for Alice's reconciliation result (matches + key)
        self.console.print()
        self.console.print("[bold bright_cyan]\\[6/7][/] Waiting for basis reconciliation from Alice...")

        got_key = self._key_ready.wait(timeout=300.0)
        if not got_key:
            display_system_message(self.console, "Timed out waiting for key.", "ERROR")
            return

        key_bits = self._received_key
        error_rate = self._received_error_rate or 0.0

        # Set key on both send and receive managers
        self.send_key_manager.set_key(list(key_bits), error_rate)
        self.recv_key_manager.set_key(list(key_bits), error_rate)

        display_bb84_interactive_result(self.console, key_bits, error_rate, 0.0, num)
        display_system_message(self.console, f"Secure key received: {len(key_bits)} bits", "SUCCESS")

    def _clear_exchange_state(self):
        """Reset all exchange synchronization state."""
        self._key_ready.clear()
        self._init_received.clear()
        self._photons_received.clear()
        self._bases_received.clear()
        self._matches_received.clear()
        self._received_photons_data = None
        self._received_bases = None
        self._received_matches = None
        self._received_key = None
        self._received_error_rate = None

    def _display_basis_comparison(self, alice_bases, bob_bases, num):
        """Display a compact basis comparison table."""
        from rich.table import Table
        from rich import box

        table = Table(box=box.SIMPLE, show_header=True, header_style="dim", padding=(0, 1))
        table.add_column("Pos", justify="center", width=4)
        table.add_column("A", justify="center", width=3)
        table.add_column("B", justify="center", width=3)
        table.add_column("", justify="center", width=3)

        show_count = min(16, num)
        for i in range(show_count):
            a = '+' if alice_bases[i] == RECTILINEAR else '×'
            b = '+' if bob_bases[i] == RECTILINEAR else '×'
            match = alice_bases[i] == bob_bases[i]
            sym = "[green]✓[/]" if match else "[red]✗[/]"
            table.add_row(str(i + 1), a, b, sym)

        self.console.print(table)

    # ─── Input Prompts ──────────────────────────────────────────

    def _prompt_bits(self, count: int) -> Optional[List[int]]:
        """Read exactly `count` bit characters (0 or 1) one at a time.
        Auto-submits when all characters are entered. Supports backspace.
        """
        import sys
        import msvcrt

        print(f"\n  {self.role} [bits] > ", end='', flush=True)
        chars = []
        while len(chars) < count:
            try:
                ch = msvcrt.getwch()
            except KeyboardInterrupt:
                print()
                return None

            if ch in ('\x03',):  # Ctrl+C
                print()
                return None
            elif ch in ('\b', '\x7f'):  # Backspace
                if chars:
                    chars.pop()
                    print('\b \b', end='', flush=True)
            elif ch in ('0', '1'):
                chars.append(ch)
                print(ch, end='', flush=True)
            # Ignore any other character silently

        print()  # newline after auto-submit
        bits = [int(c) for c in chars]
        self.console.print(f"  [dim]Bits:[/dim] {' '.join(chars)}")
        return bits

    def _prompt_bases(self, count: int) -> Optional[List[str]]:
        """Read exactly `count` basis characters one at a time.
        Valid: -  |  /  \\
        Auto-submits when all characters are entered. Supports backspace.
        """
        import sys
        import msvcrt

        valid = {'-', '|', '/', '\\'}
        print(f"\n  {self.role} [bases] > ", end='', flush=True)
        chars = []
        while len(chars) < count:
            try:
                ch = msvcrt.getwch()
            except KeyboardInterrupt:
                print()
                return None

            if ch in ('\x03',):  # Ctrl+C
                print()
                return None
            elif ch in ('\b', '\x7f'):  # Backspace
                if chars:
                    chars.pop()
                    print('\b \b', end='', flush=True)
            elif ch in valid:
                chars.append(ch)
                print(ch, end='', flush=True)
            # Ignore any other character silently

        print()  # newline after auto-submit
        self.console.print(f"  [dim]Bases:[/dim] {' '.join(chars)}")
        return chars

    # ─── Message Handling ───────────────────────────────────────

    def send_chat_message(self, text: str):
        """Encrypt and send a chat message."""
        if not self.send_key_manager.get_key():
            display_system_message(self.console, "No key! Use /refresh first.", "ERROR")
            return

        key = self.send_key_manager.get_key()
        bits_needed = len(text) * 8
        if key.remaining() < bits_needed:
            display_system_message(self.console, "Key exhausted! Use /refresh to generate a new key.", "ERROR")
            return

        try:
            ciphertext, details = encrypt_message(text, self.send_key_manager)
        except KeyExhaustedError:
            display_system_message(self.console, "Key exhausted. Use /refresh.", "ERROR")
            return

        if self.verbose:
            display_encryption(self.console, details, "SENDING")

        msg = Message(sender=self.role, content=text, encrypted=ciphertext, bits_used=details['bits_used'])
        self.history.add_message(msg)

        self.network.send(MSG_CHAT, {
            'sender': self.role,
            'ciphertext': ciphertext,
            'bits_used': details['bits_used'],
        })

        display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_sent(len(text.encode('utf-8')))

        key = self.send_key_manager.get_key()
        if key and key.needs_rotation():
            display_system_message(
                self.console,
                f"Key usage at {key.usage_percentage():.0f}%. Use /refresh for new key.",
                "WARNING"
            )

    def handle_received_message(self, msg_type: int, payload: dict, seq: int):
        """Handle an incoming network message (called from receive thread)."""
        with self._lock:
            if msg_type == MSG_CHAT:
                self._handle_chat(payload)
            elif msg_type == MSG_BB84_INIT:
                self._handle_init(payload)
            elif msg_type == MSG_BB84_PHOTONS:
                self._handle_photons(payload)
            elif msg_type == MSG_BB84_BASES:
                self._handle_bases(payload)
            elif msg_type == MSG_BB84_MATCHES:
                self._handle_matches(payload)
            elif msg_type == MSG_BB84_COMPLETE:
                self._handle_key_sync(payload)
            elif msg_type == MSG_EVE_TOGGLE:
                eve_state = payload.get('active', False)
                state_str = "enabled" if eve_state else "disabled"
                display_system_message(self.console, f"Peer toggled Eve: {state_str}", "INFO")
            elif msg_type == MSG_DISCONNECT:
                display_system_message(self.console, "Peer disconnected.", "WARNING")
                self.running = False
            elif msg_type == MSG_KEY_ROTATE:
                display_system_message(self.console, "Peer is starting new key exchange...", "INFO")
                # Bob should start his interactive exchange
                if self.role == "Bob":
                    self._clear_exchange_state()
                    # Signal that we should start waiting for photons
                    # (handled in the main thread via a flag)

    def _handle_chat(self, payload: dict):
        """Handle incoming chat message."""
        ciphertext = payload['ciphertext']
        sender = payload.get('sender', self.peer)

        if not self.recv_key_manager.get_key():
            display_system_message(self.console, "Received message but no key!", "ERROR")
            return

        try:
            plaintext, details = decrypt_message(ciphertext, self.recv_key_manager)
        except KeyExhaustedError:
            display_system_message(self.console, "Key exhausted during decrypt!", "ERROR")
            return

        if self.verbose:
            display_decryption(self.console, details)

        msg = Message(sender=sender, content=plaintext, encrypted=ciphertext,
                      bits_used=payload.get('bits_used', 0))
        self.history.add_message(msg)
        display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_received(len(plaintext.encode('utf-8')))

    def _handle_init(self, payload: dict):
        """Handle BB84 init signal from Alice (Bob's side)."""
        self._init_received.set()

    def _handle_photons(self, payload: dict):
        """Handle received photons from Alice (Bob's side)."""
        self._received_photons_data = payload.get('photons', [])
        self._photons_received.set()

    def _handle_bases(self, payload: dict):
        """Handle received bases from Bob (Alice's side)."""
        self._received_bases = payload.get('bases', [])
        self._bases_received.set()

    def _handle_matches(self, payload: dict):
        """Handle received matching positions (Bob's side)."""
        self._received_matches = payload.get('positions', [])
        self._matches_received.set()

    def _handle_key_sync(self, payload: dict):
        """Handle key received from peer."""
        key_bits = payload.get('key', [])
        error_rate = payload.get('error_rate', 0.0)
        if key_bits:
            self._received_key = key_bits
            self._received_error_rate = error_rate
            # If Bob is NOT in interactive exchange, set key directly
            if not self._photons_received.is_set():
                self.send_key_manager.set_key(list(key_bits), error_rate)
                self.recv_key_manager.set_key(list(key_bits), error_rate)
                display_system_message(
                    self.console,
                    f"Secure key received from peer: {len(key_bits)} bits",
                    "SUCCESS"
                )
            self._key_ready.set()

    # ─── Command Processing ────────────────────────────────────

    def process_command(self, cmd: str) -> bool:
        """Process a /command. Returns False if the app should quit."""
        parts = cmd.strip().split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if command == '/help':
            display_help(self.console)

        elif command == '/key':
            display_key_info(self.console, self.send_key_manager)

        elif command == '/refresh':
            self.stats.record_manual_rotation()
            try:
                self.network.send(MSG_KEY_ROTATE, {})
            except Exception:
                pass
            if self.role == "Alice":
                self.interactive_key_exchange_alice()
            else:
                self.interactive_key_exchange_bob()

        elif command == '/stats':
            display_stats(self.console, self.stats, self.send_key_manager,
                          self.role, self.peer_address)

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
            display_header(self.console, self.role, self.peer, self.send_key_manager, self.stats)

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

        # Start receiving thread FIRST so we can handle incoming messages
        self.network.start_receiving(self.handle_received_message)

        # Interactive key exchange based on role
        if self.role == "Alice":
            self.interactive_key_exchange_alice()
        else:
            self.interactive_key_exchange_bob()

        # Display header and status
        display_header(self.console, self.role, self.peer, self.send_key_manager, self.stats)
        display_status_bar(self.console, self.send_key_manager, self.stats)

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
        self.send_key_manager.clear()
        self.recv_key_manager.clear()
        self.network.stop()
        display_system_message(self.console, "Keys cleared from memory. Goodbye!", "SUCCESS")
