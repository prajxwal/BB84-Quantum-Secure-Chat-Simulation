#!/usr/bin/env python3
"""
BB84 Quantum Secure Chat — Single-File Bundle
Run with: curl -sL <url> | python3
Or:       python bb84.py
"""

# ─── Auto-install dependencies ──────────────────────────────────
import subprocess, sys

def _ensure_deps():
    for pkg in ('rich', 'colorama'):
        try:
            __import__(pkg)
        except ImportError:
            print(f"Installing {pkg}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', pkg])

_ensure_deps()

# ─── Standard library imports ───────────────────────────────────
import hashlib, hmac, json, os, random, secrets, socket, struct, threading, time, uuid
from datetime import datetime, timedelta
from typing import Any, Callable, List, Optional, Tuple

# ─── Cross-platform getch ──────────────────────────────────────
try:
    import msvcrt
    def _getch():
        return msvcrt.getwch()
except ImportError:
    import tty, termios
    def _getch():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ─── Rich imports ───────────────────────────────────────────────
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.theme import Theme
from rich import box

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
RECTILINEAR = 0
DIAGONAL = 1
BASIS_SYMBOLS = {RECTILINEAR: '+', DIAGONAL: '×'}
INTERACTIVE_SYMBOLS = {'-': (0, RECTILINEAR), '|': (1, RECTILINEAR), '/': (0, DIAGONAL), '\\': (1, DIAGONAL)}
BIT_BASIS_TO_SYMBOL = {(0, RECTILINEAR): '-', (1, RECTILINEAR): '|', (0, DIAGONAL): '/', (1, DIAGONAL): '\\'}
ANGLES = {(0, RECTILINEAR): 0, (1, RECTILINEAR): 90, (0, DIAGONAL): 45, (1, DIAGONAL): 135}
ANGLE_SYMBOLS = {0: '-', 90: '|', 45: '/', 135: '\\'}

MSG_CHAT = 0x01; MSG_BB84_INIT = 0x10; MSG_BB84_PHOTONS = 0x11
MSG_BB84_BASES = 0x12; MSG_BB84_MATCHES = 0x13; MSG_BB84_SAMPLE = 0x14
MSG_BB84_VERIFY = 0x15; MSG_BB84_COMPLETE = 0x16; MSG_BB84_ABORT = 0x17
MSG_KEY_ROTATE = 0x20; MSG_COMMAND = 0x30; MSG_STATUS = 0x40
MSG_EVE_TOGGLE = 0x50; MSG_DISCONNECT = 0xFE; MSG_ERROR = 0xFF

# ═══════════════════════════════════════════════════════════════
# SETTINGS
# ═══════════════════════════════════════════════════════════════
HOST = 'localhost'; PORT = 5000; BUFFER_SIZE = 8192
CONNECTION_TIMEOUT = 30; RETRY_ATTEMPTS = 3; RETRY_BACKOFF = [1, 2, 4]
NUM_PHOTONS = 256; INTERACTIVE_NUM_PHOTONS = 16; MIN_KEY_LENGTH = 2
MAX_KEY_LENGTH = 128; ERROR_THRESHOLD = 0.10; SAMPLE_FRACTION = 0.25
KEY_ROTATION_THRESHOLD = 0.75; AUTO_ROTATION = True
ANIMATION_SPEED = 0.03; SHOW_ENCRYPTION_DETAILS = True; ENABLE_STATISTICS = True

# ═══════════════════════════════════════════════════════════════
# UI COLORS & SYMBOLS
# ═══════════════════════════════════════════════════════════════
COLORS = {
    'alice': 'bold cyan', 'bob': 'bold green', 'system': 'bold yellow',
    'error': 'bold red', 'warning': 'bold bright_yellow', 'success': 'bold green',
    'encrypted': 'dim white', 'key': 'bold magenta', 'header': 'bold white on blue',
    'secure': 'bold green', 'compromised': 'bold red', 'eve': 'bold red',
    'info': 'cyan', 'dim': 'dim', 'highlight': 'bold bright_white',
    'phase': 'bold bright_cyan', 'photon': 'bright_magenta',
    'basis_match': 'green', 'basis_miss': 'red', 'bit': 'bright_white',
    'angle': 'bright_yellow', 'progress': 'bright_green',
}
CHAT_THEME = Theme({k: v for k, v in COLORS.items() if k in (
    'alice','bob','system','error','warning','success','encrypted','key',
    'secure','compromised','eve','info','dim','highlight','phase','photon')})
SYMBOLS = {
    'secure': '🟢', 'warning': '⚠️ ', 'compromised': '🔴', 'lock': '🔒',
    'unlock': '🔓', 'key': '🔑', 'send': '~~~>', 'receive': '<~~~',
    'check': '✓', 'cross': '✗', 'photon': '◆', 'antenna': '📡',
    'shield': '🛡️', 'eye': '👁️',
}

# ═══════════════════════════════════════════════════════════════
# PHOTON
# ═══════════════════════════════════════════════════════════════
class Photon:
    __slots__ = ('bit', 'basis', 'angle', 'timestamp')
    def __init__(self, bit, basis, angle=None):
        self.bit = bit; self.basis = basis
        self.angle = angle if angle is not None else ANGLES[(bit, basis)]
        self.timestamp = time.time()
    def to_dict(self): return {'bit': self.bit, 'basis': self.basis, 'angle': self.angle}
    @classmethod
    def from_dict(cls, d): return cls(bit=d['bit'], basis=d['basis'], angle=d['angle'])
    @property
    def basis_symbol(self): return BASIS_SYMBOLS.get(self.basis, '?')
    @property
    def angle_symbol(self): return ANGLE_SYMBOLS.get(self.angle, '?')

# ═══════════════════════════════════════════════════════════════
# BB84 PROTOCOL
# ═══════════════════════════════════════════════════════════════
def generate_random_bits(n): return [secrets.randbelow(2) for _ in range(n)]
def generate_random_bases(n): return [secrets.randbelow(2) for _ in range(n)]
def encode_photon(bit, basis): return Photon(bit=bit, basis=basis, angle=ANGLES[(bit, basis)])
def encode_photons(bits, bases): return [encode_photon(b, ba) for b, ba in zip(bits, bases)]
def measure_photon(photon, basis): return photon.bit if photon.basis == basis else random.randint(0, 1)
def measure_photons(photons, bases): return [measure_photon(p, b) for p, b in zip(photons, bases)]
def find_matching_positions(a_bases, b_bases): return [i for i in range(len(a_bases)) if a_bases[i] == b_bases[i]]
def extract_key_bits(bits, positions): return [bits[i] for i in positions]

def check_errors(alice_key, bob_key, sample_fraction=SAMPLE_FRACTION):
    n = len(alice_key); sample_size = max(1, int(n * sample_fraction))
    sample_positions = sorted(random.sample(range(n), min(sample_size, n)))
    a_s = [alice_key[i] for i in sample_positions]; b_s = [bob_key[i] for i in sample_positions]
    errors = sum(a != b for a, b in zip(a_s, b_s))
    return (errors / len(sample_positions) if sample_positions else 0.0), sample_positions, a_s, b_s

def remove_sample_bits(key, sample_positions):
    s = set(sample_positions); return [b for i, b in enumerate(key) if i not in s]

class Eve:
    def __init__(self):
        self.intercepted_count = 0; self.last_bases = []; self.last_bits = []
    def intercept(self, photons):
        n = len(photons); eve_bases = generate_random_bases(n)
        eve_bits = []; modified_photons = []
        for photon, eve_basis in zip(photons, eve_bases):
            m_bit = measure_photon(photon, eve_basis); eve_bits.append(m_bit)
            modified_photons.append(encode_photon(m_bit, eve_basis))
        self.intercepted_count += n; self.last_bases = eve_bases; self.last_bits = eve_bits
        return modified_photons, eve_bits, eve_bases

# ═══════════════════════════════════════════════════════════════
# CRYPTO UTILITIES
# ═══════════════════════════════════════════════════════════════
def text_to_binary(text):
    bits = []
    for c in text: bits.extend(int(b) for b in format(ord(c), '08b'))
    return bits

def binary_to_text(bits):
    chars = []
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        if len(byte) < 8: break
        chars.append(chr(int(''.join(str(b) for b in byte), 2)))
    return ''.join(chars)

def binary_to_hex(bits):
    h = ''
    for i in range(0, len(bits), 4):
        nib = bits[i:i+4]
        if len(nib) < 4: nib.extend([0]*(4-len(nib)))
        h += format(int(''.join(str(b) for b in nib), 2), 'x')
    return h

def hex_to_binary(hex_str):
    bits = []
    for c in hex_str: bits.extend(int(b) for b in format(int(c, 16), '04b'))
    return bits

def bits_to_string(bits):
    s = ''.join(str(b) for b in bits); return ' '.join(s[i:i+8] for i in range(0, len(s), 8))

def key_to_hex(bits): return binary_to_hex(bits)

# ═══════════════════════════════════════════════════════════════
# KEY MANAGER (with HKDF expansion)
# ═══════════════════════════════════════════════════════════════
EXPANDED_KEY_BITS = 1024

class KeyExhaustedError(Exception): pass

def expand_key_bits(seed_bits, length=EXPANDED_KEY_BITS):
    seed_str = ''.join(str(b) for b in seed_bits)
    seed_bytes = hashlib.sha256(seed_str.encode()).digest()
    expanded = []; counter = 0; prev = b''
    while len(expanded) < length:
        block = hmac.new(seed_bytes, prev + counter.to_bytes(4, 'big'), hashlib.sha256).digest()
        prev = block
        for byte in block:
            for i in range(7, -1, -1):
                expanded.append((byte >> i) & 1)
                if len(expanded) >= length: break
            if len(expanded) >= length: break
        counter += 1
    return expanded[:length]

class EncryptionKey:
    def __init__(self, key_bits, error_rate=0.0):
        self.id = str(uuid.uuid4())[:8]
        self.seed_bits = list(key_bits); self.seed_length = len(self.seed_bits)
        self.bits = expand_key_bits(key_bits, EXPANDED_KEY_BITS)
        self.length = len(self.bits)
        self.generated_at = datetime.now(); self.bits_used = 0; self.error_rate = error_rate
    def consume(self, n):
        if self.bits_used + n > self.length:
            raise KeyExhaustedError(f"Need {n} bits but only {self.remaining()} remain")
        consumed = self.bits[self.bits_used:self.bits_used+n]; self.bits_used += n; return consumed
    def remaining(self): return self.length - self.bits_used
    def usage_percentage(self): return 100.0 if self.length == 0 else (self.bits_used/self.length)*100.0
    def needs_rotation(self): return self.usage_percentage() >= (KEY_ROTATION_THRESHOLD*100)
    def age_seconds(self): return (datetime.now() - self.generated_at).total_seconds()

class KeyManager:
    def __init__(self):
        self.current_key = None; self.key_history = []
        self.keys_generated = 0; self.keys_compromised = 0
    def set_key(self, key_bits, error_rate=0.0):
        if self.current_key:
            self.key_history.append({'id': self.current_key.id, 'length': self.current_key.length,
                'bits_used': self.current_key.bits_used})
        self.current_key = EncryptionKey(key_bits, error_rate); self.keys_generated += 1
        return self.current_key
    def get_key(self): return self.current_key
    def consume_bits(self, n):
        if not self.current_key: raise KeyExhaustedError("No key available")
        return self.current_key.consume(n)
    def needs_rotation(self): return True if not self.current_key else self.current_key.needs_rotation()
    def mark_compromised(self): self.keys_compromised += 1; self.current_key = None
    def clear(self):
        if self.current_key: self.current_key.bits = [0]*len(self.current_key.bits); self.current_key = None

# ═══════════════════════════════════════════════════════════════
# ENCRYPTION
# ═══════════════════════════════════════════════════════════════
def xor_bits(data, key): return [d ^ k for d, k in zip(data, key)]

def encrypt_message(message, key_manager):
    msg_bits = text_to_binary(message); n = len(msg_bits)
    key_bits = key_manager.consume_bits(n); cipher_bits = xor_bits(msg_bits, key_bits)
    ciphertext_hex = binary_to_hex(cipher_bits)
    return ciphertext_hex, {'message': message, 'message_bits': msg_bits, 'key_bits': key_bits,
        'cipher_bits': cipher_bits, 'ciphertext_hex': ciphertext_hex, 'bits_used': n}

def decrypt_message(ciphertext_hex, key_manager):
    cipher_bits = hex_to_binary(ciphertext_hex); n = len(cipher_bits)
    key_bits = key_manager.consume_bits(n); msg_bits = xor_bits(cipher_bits, key_bits)
    plaintext = binary_to_text(msg_bits)
    return plaintext, {'ciphertext_hex': ciphertext_hex, 'cipher_bits': cipher_bits,
        'key_bits': key_bits, 'message_bits': msg_bits, 'plaintext': plaintext, 'bits_used': n}

# ═══════════════════════════════════════════════════════════════
# NETWORK PROTOCOL
# ═══════════════════════════════════════════════════════════════
HEADER_FORMAT = '!BIi'; HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
class ProtocolError(Exception): pass
_sequence_counter = 0
def _next_sequence():
    global _sequence_counter; _sequence_counter += 1; return _sequence_counter

def pack_message(msg_type, payload, seq=None):
    if seq is None: seq = _next_sequence()
    payload_bytes = json.dumps(payload).encode('utf-8')
    return struct.pack(HEADER_FORMAT, msg_type, len(payload_bytes), seq) + payload_bytes

def unpack_header(data):
    if len(data) < HEADER_SIZE: raise ProtocolError(f"Header too short")
    return struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])

def unpack_payload(data): return json.loads(data.decode('utf-8'))

def _recv_exactly(sock, num_bytes):
    data = b''
    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))
        if not chunk: return None
        data += chunk
    return data

def recv_message(sock):
    header_data = _recv_exactly(sock, HEADER_SIZE)
    if not header_data: raise ProtocolError("Connection closed")
    msg_type, payload_len, seq = unpack_header(header_data)
    if payload_len > 0:
        payload_data = _recv_exactly(sock, payload_len)
        if not payload_data: raise ProtocolError("Connection closed during payload read")
        payload = unpack_payload(payload_data)
    else:
        payload = {}
    return msg_type, payload, seq

def send_message(sock, msg_type, payload):
    sock.sendall(pack_message(msg_type, payload))

# ═══════════════════════════════════════════════════════════════
# SERVER
# ═══════════════════════════════════════════════════════════════
class Server:
    def __init__(self, host='0.0.0.0', port=PORT):
        self.host = host; self.port = port
        self.server_socket = None; self.client_socket = None
        self.client_address = None; self.running = False; self._on_message = None
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port)); self.server_socket.listen(1); self.running = True
    def accept_connection(self):
        self.client_socket, self.client_address = self.server_socket.accept()
        self.client_socket.settimeout(None); return self.client_address
    def send(self, msg_type, payload): send_message(self.client_socket, msg_type, payload)
    def start_receiving(self, callback):
        self._on_message = callback
        t = threading.Thread(target=self._receive_loop, daemon=True); t.start()
    def _receive_loop(self):
        while self.running and self.client_socket:
            try:
                msg_type, payload, seq = recv_message(self.client_socket)
                if self._on_message: self._on_message(msg_type, payload, seq)
            except socket.timeout: continue
            except (ProtocolError, ConnectionError, OSError):
                if self.running: self.running = False
                break
            except Exception:
                if self.running: self.running = False
                break
    def stop(self):
        self.running = False
        for s in (self.client_socket, self.server_socket):
            if s:
                try: s.close()
                except: pass

# ═══════════════════════════════════════════════════════════════
# CLIENT
# ═══════════════════════════════════════════════════════════════
class Client:
    def __init__(self, host='localhost', port=PORT):
        self.host = host; self.port = port; self.socket = None
        self.running = False; self._on_message = None
    def connect(self, retries=RETRY_ATTEMPTS):
        for attempt in range(retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(CONNECTION_TIMEOUT)
                self.socket.connect((self.host, self.port))
                self.socket.settimeout(None); self.running = True; return True
            except (ConnectionRefusedError, socket.timeout, OSError):
                if attempt < retries - 1:
                    time.sleep(RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)])
                else: return False
    def send(self, msg_type, payload): send_message(self.socket, msg_type, payload)
    def start_receiving(self, callback):
        self._on_message = callback
        t = threading.Thread(target=self._receive_loop, daemon=True); t.start()
    def _receive_loop(self):
        while self.running and self.socket:
            try:
                msg_type, payload, seq = recv_message(self.socket)
                if self._on_message: self._on_message(msg_type, payload, seq)
            except socket.timeout: continue
            except (ProtocolError, ConnectionError, OSError):
                if self.running: self.running = False
                break
            except Exception:
                if self.running: self.running = False
                break
    def stop(self):
        self.running = False
        if self.socket:
            try: self.socket.close()
            except: pass

# ═══════════════════════════════════════════════════════════════
# MESSAGE & HISTORY
# ═══════════════════════════════════════════════════════════════
class Message:
    def __init__(self, sender, content, encrypted='', bits_used=0):
        self.id = str(uuid.uuid4())[:8]; self.sender = sender
        self.content = content; self.encrypted = encrypted
        self.timestamp = datetime.now(); self.bits_used = bits_used
    def time_str(self): return self.timestamp.strftime('%H:%M:%S')

class ChatHistory:
    def __init__(self): self.messages = []; self.system_messages = []
    def add_message(self, msg): self.messages.append(msg)
    def add_system(self, text, level='INFO'):
        self.system_messages.append({'text': text, 'level': level, 'timestamp': datetime.now()})
    def get_all(self): return list(self.messages)
    def count(self): return len(self.messages)
    def total_data(self): return sum(len(m.content.encode('utf-8')) for m in self.messages)
    def export(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"BB84 Quantum Chat Transcript\nExported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total messages: {self.count()}\n{'='*60}\n\n")
            for msg in self.messages:
                f.write(f"[{msg.time_str()}] {msg.sender}: {msg.content}\n")
                if msg.encrypted: f.write(f"           [ENCRYPTED] {msg.encrypted}\n")
                f.write("\n")

# ═══════════════════════════════════════════════════════════════
# STATISTICS
# ═══════════════════════════════════════════════════════════════
class Statistics:
    def __init__(self):
        self.connected_at = None; self.last_activity = datetime.now()
        self.messages_sent = 0; self.messages_received = 0
        self.data_encrypted = 0; self.data_decrypted = 0
        self.keys_generated = 0; self.keys_compromised = 0
        self.auto_rotations = 0; self.manual_rotations = 0
        self.total_photons_sent = 0; self.total_basis_matches = 0
        self.last_match_rate = 0.0; self.last_error_rate = 0.0
        self.last_key_length = 0; self.exchange_count = 0
        self.exchange_match_rates = []; self.exchange_error_rates = []
        self.exchange_durations = []; self.eavesdropper_detected_count = 0
        self.eve_active = False; self.last_security_check = datetime.now()
    def mark_connected(self): self.connected_at = datetime.now(); self.last_activity = datetime.now()
    def record_message_sent(self, n): self.messages_sent += 1; self.data_encrypted += n; self.last_activity = datetime.now()
    def record_message_received(self, n): self.messages_received += 1; self.data_decrypted += n; self.last_activity = datetime.now()
    def record_key_exchange(self, photons, matches, match_rate, error_rate, key_length, duration):
        self.keys_generated += 1; self.exchange_count += 1; self.total_photons_sent += photons
        self.total_basis_matches += matches; self.last_match_rate = match_rate
        self.last_error_rate = error_rate; self.last_key_length = key_length
        self.exchange_match_rates.append(match_rate); self.exchange_error_rates.append(error_rate)
        self.exchange_durations.append(duration); self.last_activity = datetime.now()
    def record_manual_rotation(self): self.manual_rotations += 1
    def total_messages(self): return self.messages_sent + self.messages_received
    def total_data(self): return self.data_encrypted + self.data_decrypted
    def uptime_str(self):
        if not self.connected_at: return "00:00:00"
        td = datetime.now() - self.connected_at; s = int(td.total_seconds())
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"
    def avg_match_rate(self): return sum(self.exchange_match_rates)/len(self.exchange_match_rates) if self.exchange_match_rates else 0.0
    def avg_error_rate(self): return sum(self.exchange_error_rates)/len(self.exchange_error_rates) if self.exchange_error_rates else 0.0
    def security_status(self):
        if self.eavesdropper_detected_count > 0 and self.last_error_rate > 0.10: return "COMPROMISED"
        if self.eve_active: return "EVE ACTIVE"
        return "SECURE"

# ═══════════════════════════════════════════════════════════════
# UI FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def create_console(): return Console(theme=CHAT_THEME, highlight=False)

def display_header(console, role, peer, key_manager, stats):
    key = key_manager.get_key(); key_len = key.length if key else 0
    key_usage = f"{key.usage_percentage():.0f}%" if key else "N/A"
    msg_count = stats.total_messages(); error_rate = stats.last_error_rate
    sec_status = stats.security_status()
    sec_sym = SYMBOLS['secure'] if sec_status == "SECURE" else SYMBOLS['compromised']
    console.print(f"[bold bright_cyan]─── BB84 Quantum Chat ───[/] [dim]Key:{key_len}b ({key_usage}) │ "
                  f"Msgs:{msg_count} │ Err:{error_rate:.1%} │ {sec_sym} {sec_status}[/]")
    console.print()

def display_message(console, msg, show_encrypted=True):
    style = "bold cyan" if msg.sender.lower() == "alice" else "bold green"
    console.print(f"[dim]{msg.time_str()}[/] [{style}]<{msg.sender}>[/] {msg.content}")
    if show_encrypted and msg.encrypted:
        console.print(f"         [dim]│ {SYMBOLS['lock']} {msg.encrypted}[/]")

def display_system_message(console, text, level="INFO"):
    time_str = datetime.now().strftime('%H:%M:%S')
    prefixes = {'INFO': ('[dim]', '---'), 'WARNING': ('[bold yellow]', '⚠ '),
                'ERROR': ('[bold red]', '!!!'), 'SUCCESS': ('[bold green]', '>>>')}
    style, prefix = prefixes.get(level, ('[dim]', '---'))
    console.print(f"[dim]{time_str}[/] {style}{prefix} {text}[/]")

def display_status_bar(console, key_manager, stats):
    key = key_manager.get_key()
    if key:
        usage_pct = key.usage_percentage(); bar_len = 20
        filled = int(bar_len * usage_pct / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        age = int(key.age_seconds()); age_str = f"{age//60}m" if age >= 60 else f"{age}s"
        console.print(f"[dim]─── Key:[/] [{bar}] [dim]{usage_pct:.0f}% ({key.bits_used}/{key.length}b) │ Age: {age_str} ───[/]")
    else:
        console.print("[dim]─── No key. Type /refresh to generate. ───[/]")
    console.print()

def display_key_info(console, key_manager):
    key = key_manager.get_key()
    if not key:
        display_system_message(console, "No key established. Use /refresh.", "WARNING"); return
    key_hex = key_to_hex(key.bits[:64])
    console.print(f"[dim]───────── Encryption Key ─────────[/]")
    console.print(f"  [bold magenta]ID:[/]        #{key.id}")
    console.print(f"  [bold magenta]Length:[/]    {key.length} bits")
    console.print(f"  [bold magenta]Age:[/]       {int(key.age_seconds())}s")
    console.print(f"  [bold magenta]Error:[/]     {key.error_rate:.1%}")
    console.print(f"  [bold magenta]Hex:[/]       {key_hex}")
    console.print(f"  [bold magenta]Used:[/]      {key.bits_used}/{key.length} ({key.usage_percentage():.0f}%)")
    console.print(f"  [bold magenta]Remaining:[/] {key.remaining()} bits")
    console.print(f"[dim]──────────────────────────────────[/]")

def display_welcome(console, role):
    console.print()
    console.print("[bold bright_cyan]╔══════════════════════════════════════════════╗[/]")
    console.print("[bold bright_cyan]║[/]  [bold bright_white]BB84 QUANTUM SECURE CHAT[/]                   [bold bright_cyan]║[/]")
    console.print("[bold bright_cyan]║[/]  [dim]Quantum Key Distribution • XOR Encryption[/] [bold bright_cyan]║[/]")
    console.print("[bold bright_cyan]╚══════════════════════════════════════════════╝[/]")
    console.print()
    console.print(f"  [dim]Role:[/] [bold]{role}[/]  [dim]│  Type[/] [bold]/help[/] [dim]for commands[/]")
    console.print()

def display_chat_history(console, history, show_encrypted=True):
    messages = history.get_all()
    if not messages: display_system_message(console, "No messages yet.", "INFO"); return
    console.print(f"[dim]─── Message History ({len(messages)} messages) ───[/]")
    for msg in messages: display_message(console, msg, show_encrypted)
    console.print(f"[dim]─── End of History ───[/]")

def display_encryption(console, details, direction="SENDING"):
    console.print(f"[dim]  ┌─ Encrypt: \"{details['message']}\"[/]")
    console.print(f"[dim]  │ Msg: {bits_to_string(details['message_bits'][:24])} ...[/]")
    console.print(f"[dim]  │ Key: {bits_to_string(details['key_bits'][:24])} ...[/]")
    console.print(f"[dim]  │ XOR: {bits_to_string(details['cipher_bits'][:24])} ...[/]")
    console.print(f"[dim]  └─ Cipher:[/] [bold magenta]{details['ciphertext_hex']}[/] [dim]({details['bits_used']}b used)[/]")

def display_decryption(console, details):
    console.print(f"[dim]  ┌─ Decrypt: {details['ciphertext_hex']}[/]")
    console.print(f"[dim]  └─ Plain:[/] [bold green]{details['plaintext']}[/] [dim]({details['bits_used']}b)[/]")

def display_bb84_interactive_result(console, final_key, error_rate, match_rate, num_photons):
    console.print()
    if len(final_key) < 1:
        console.print(f"[bold red]╔══ ⚠  KEY EXCHANGE FAILED ══╗[/]")
        console.print(f"[bold red]║[/] No shared key could be established")
        console.print(f"[bold red]║[/] Try again with /refresh")
        console.print(f"[bold red]╚═══════════════════════════════════╝[/]")
    else:
        key_hex = key_to_hex(final_key[:64]); seed_len = len(final_key)
        console.print(f"[bold green]╔══ 🟢 SECURE KEY ESTABLISHED ══╗[/]")
        console.print(f"[bold green]║[/] Length: {seed_len} bits → {EXPANDED_KEY_BITS}b expanded │ Error: {error_rate:.1%}")
        console.print(f"[bold green]║[/] Key: [dim]{key_hex}[/]")
        console.print(f"[bold green]╚═══════════════════════════════════╝[/]")
    console.print()

def display_help(console):
    console.print()
    console.print("[bold bright_cyan]═══ BB84 Quantum Chat Help ═══[/]"); console.print()
    console.print("[bold]Commands:[/]")
    for cmd, desc in [("/help","Show this help"), ("/key","Show current encryption key"),
                      ("/refresh","Generate new BB84 key (interactive)"), ("/stats","Show statistics"),
                      ("/verbose on|off","Toggle encryption details"), ("/clear","Clear screen"),
                      ("/history","Show message history"), ("/export","Export transcript"),
                      ("/eve","Toggle Eve eavesdropper simulation"), ("/quit","Exit (also Ctrl+C)")]:
        console.print(f"  [bold]{cmd}[/]  {desc}")
    console.print()
    console.print("[bold]BB84 Bases:[/]  [bold]-[/] horizontal  [bold]|[/] vertical  [bold]/[/] diagonal  [bold]\\[/] anti-diag")
    console.print()

def display_stats(console, stats, key_manager, role, peer_address=""):
    sec_status = stats.security_status()
    sec_sym = SYMBOLS['secure'] if sec_status == "SECURE" else SYMBOLS['compromised']
    console.print(); console.print("[bold bright_cyan]═══ Quantum Channel Statistics ═══[/]"); console.print()
    console.print("[bold]Connection[/]")
    console.print(f"  Status:        {sec_sym} ACTIVE"); console.print(f"  Role:          {role}")
    if peer_address: console.print(f"  Peer:          {peer_address}")
    console.print(f"  Uptime:        {stats.uptime_str()}"); console.print()
    console.print("[bold]Messages[/]")
    console.print(f"  Sent:          {stats.messages_sent}"); console.print(f"  Received:      {stats.messages_received}"); console.print()
    key = key_manager.get_key(); console.print("[bold]Current Key[/]")
    if key:
        usage = key.usage_percentage(); bar_len = 20; filled = int(bar_len * usage / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        console.print(f"  ID:            #{key.id}"); console.print(f"  Length:        {key.length} bits")
        console.print(f"  Usage:         [{bar}] {usage:.0f}%"); console.print(f"  Remaining:     {key.remaining()} bits")
    else: console.print("  [dim]No key established[/]")
    console.print(); console.print("[bold]BB84 Protocol[/]")
    console.print(f"  Exchanges:     {stats.exchange_count}"); console.print(f"  Compromised:   {stats.keys_compromised}")
    if stats.exchange_count > 0:
        console.print(f"  Avg match:     {stats.avg_match_rate():.1%}")
        console.print(f"  Avg error:     {stats.avg_error_rate():.1%}")
    console.print()

# ═══════════════════════════════════════════════════════════════
# CHAT MANAGER
# ═══════════════════════════════════════════════════════════════
class ChatManager:
    def __init__(self, role, network):
        self.role = role; self.peer = "Bob" if role == "Alice" else "Alice"
        self.network = network; self.console = create_console()
        self.send_key_manager = KeyManager(); self.recv_key_manager = KeyManager()
        self.history = ChatHistory(); self.stats = Statistics()
        self.verbose = False; self.running = True; self._lock = threading.Lock()
        self.peer_address = ""
        self._key_ready = threading.Event(); self._init_received = threading.Event()
        self._photons_received = threading.Event(); self._bases_received = threading.Event()
        self._matches_received = threading.Event()
        self._received_photons_data = None; self._received_bases = None
        self._received_matches = None; self._received_key = None; self._received_error_rate = None

    def interactive_key_exchange_alice(self):
        num = INTERACTIVE_NUM_PHOTONS; self._clear_exchange_state()
        try: self.network.send(MSG_BB84_INIT, {'num_photons': num})
        except: pass
        self.console.print(); self.console.print("[bold bright_cyan]═══ BB84 Interactive Key Exchange ═══[/]")
        self.console.print(f"[dim]You will prepare {num} photons for Bob.[/dim]"); self.console.print()
        self.console.print("[bold bright_cyan]\\[1/7][/] Enter your random bits (0 or 1, space-separated):")
        self.console.print(f"[dim]  Need {num} bits. Example: 1 0 1 1 0 0 1 0 1 1 0 0 1 0 1 0[/dim]")
        alice_bits = self._prompt_bits(num)
        if alice_bits is None: return
        self.console.print(); self.console.print("[bold bright_cyan]\\[2/7][/] Enter your bases for each bit:")
        self.console.print("  [dim]Use polarization symbols:[/dim]  [bold]-[/]  [bold]|[/]  [bold]/[/]  [bold]\\\\[/]")
        self.console.print("  [dim]- and | are rectilinear,  / and \\\\ are diagonal[/dim]")
        self.console.print(f"  [dim]Need {num} symbols. Example: - | / \\\\ | - / \\\\ - | / \\\\ | - / \\\\[/dim]")
        alice_bases_input = self._prompt_bases(num)
        if alice_bases_input is None: return
        alice_bases = [RECTILINEAR if s in ('-','|') else DIAGONAL for s in alice_bases_input]
        self.console.print(); self.console.print("[bold bright_cyan]\\[3/7][/] Encoding photons...")
        photons = encode_photons(alice_bits, alice_bases)
        polarizations = ' '.join(BIT_BASIS_TO_SYMBOL.get((p.bit, p.basis), '?') for p in photons)
        self.console.print(f"  [dim]Your photons:[/dim] [bright_yellow]{polarizations}[/]")
        if self.stats.eve_active:
            eve = Eve()
            photons, _, _ = eve.intercept(photons)
            self.console.print(f"  [bold red]{SYMBOLS['warning']} Eve intercepted and modified the photons![/]")
        self.console.print(); self.console.print("[bold bright_cyan]\\[4/7][/] Transmitting photons to Bob...")
        self.console.print("  Alice [bright_yellow]~~~> ~~~> ~~~> ~~~>[/] Bob")
        try: self.network.send(MSG_BB84_PHOTONS, {'photons': [p.to_dict() for p in photons]})
        except Exception as e: display_system_message(self.console, f"Failed: {e}", "ERROR"); return
        self.console.print(); self.console.print("[bold bright_cyan]\\[5/7][/] Waiting for Bob to measure photons...")
        if not self._bases_received.wait(timeout=300.0):
            display_system_message(self.console, "Timed out waiting for Bob's bases.", "ERROR"); return
        bob_bases = self._received_bases
        bob_bases_symbols = ' '.join('- |' if b == RECTILINEAR else '/ \\' for b in bob_bases)
        self.console.print(f"  [dim]Bob's bases:[/dim] [bright_magenta]{bob_bases_symbols}[/]")
        self.console.print(); self.console.print("[bold bright_cyan]\\[6/7][/] Basis reconciliation...")
        matching_positions = find_matching_positions(alice_bases, bob_bases)
        match_rate = len(matching_positions) / num
        self._display_basis_comparison(alice_bases, bob_bases, num)
        match_preview = ', '.join(str(p+1) for p in matching_positions[:10])
        if len(matching_positions) > 10: match_preview += '...'
        self.console.print(f"  [dim]Matching positions:[/dim] [green]{match_preview}[/]")
        self.console.print(f"  [dim]Match rate:[/dim] {match_rate:.1%} ({len(matching_positions)}/{num})")
        self.network.send(MSG_BB84_MATCHES, {'positions': matching_positions, 'alice_bases': alice_bases})
        alice_raw_key = extract_key_bits(alice_bits, matching_positions)
        self.console.print(); self.console.print("[bold bright_cyan]\\[7/7][/] Error checking...")
        error_rate, sample_positions, _, _ = check_errors(alice_raw_key, alice_raw_key)
        alice_final_key = remove_sample_bits(alice_raw_key, sample_positions)
        if len(alice_final_key) < 1:
            display_system_message(self.console, "Key too short! Try again with /refresh.", "ERROR"); return
        self.send_key_manager.set_key(list(alice_final_key), 0.0)
        self.recv_key_manager.set_key(list(alice_final_key), 0.0); self._key_ready.set()
        try: self.network.send(MSG_BB84_COMPLETE, {'key': alice_final_key, 'error_rate': 0.0})
        except: pass
        display_bb84_interactive_result(self.console, alice_final_key, 0.0, match_rate, num)
        self.stats.record_key_exchange(photons=num, matches=len(matching_positions),
            match_rate=match_rate, error_rate=0.0, key_length=len(alice_final_key), duration=0.0)

    def interactive_key_exchange_bob(self):
        num = INTERACTIVE_NUM_PHOTONS; self._clear_exchange_state()
        self.console.print(); self.console.print("[bold bright_cyan]═══ BB84 Interactive Key Exchange ═══[/]")
        self.console.print("[dim]Waiting for Alice to prepare photons...[/dim]")
        self.console.print("[dim](Alice is entering her bits and bases)[/dim]"); self.console.print()
        if not self._photons_received.wait(timeout=600.0):
            display_system_message(self.console, "Timed out waiting for Alice's photons.", "ERROR"); return
        photons = [Photon.from_dict(d) for d in self._received_photons_data]; num = len(photons)
        self.console.print(f"[bold bright_cyan]\\[4/7][/] Received {num} photons from Alice!")
        self.console.print("  Alice [bright_yellow]~~~> ~~~> ~~~> ~~~>[/] Bob"); self.console.print()
        self.console.print("[bold bright_cyan]\\[5/7][/] Choose your measurement bases:")
        self.console.print("  [dim]Use polarization symbols:[/dim]  [bold]-[/]  [bold]|[/]  [bold]/[/]  [bold]\\\\[/]")
        self.console.print("  [dim]- and | are rectilinear,  / and \\\\ are diagonal[/dim]")
        self.console.print(f"  [dim]Need {num} symbols. Example: | - \\\\ / - | \\\\ / | - \\\\ / - | \\\\ /[/dim]")
        bob_bases_input = self._prompt_bases(num)
        if bob_bases_input is None: return
        bob_bases = [RECTILINEAR if s in ('-','|') else DIAGONAL for s in bob_bases_input]
        bob_bits = measure_photons(photons, bob_bases)
        measured_symbols = ' '.join(BIT_BASIS_TO_SYMBOL.get((b, ba), '?') for b, ba in zip(bob_bits, bob_bases))
        self.console.print(f"  [dim]Your measurements:[/dim] [bright_yellow]{measured_symbols}[/]")
        self.console.print(f"  [dim]Measured bits:[/dim] {' '.join(str(b) for b in bob_bits)}")
        self.console.print(); self.console.print("[dim]Sending your bases to Alice...[/dim]")
        self.network.send(MSG_BB84_BASES, {'bases': bob_bases})
        self.console.print(); self.console.print("[bold bright_cyan]\\[6/7][/] Waiting for basis reconciliation from Alice...")
        if not self._key_ready.wait(timeout=300.0):
            display_system_message(self.console, "Timed out waiting for key.", "ERROR"); return
        key_bits = self._received_key; error_rate = self._received_error_rate or 0.0
        self.send_key_manager.set_key(list(key_bits), error_rate)
        self.recv_key_manager.set_key(list(key_bits), error_rate)
        display_bb84_interactive_result(self.console, key_bits, error_rate, 0.0, num)
        display_system_message(self.console, f"Secure key received: {len(key_bits)} bits", "SUCCESS")

    def _clear_exchange_state(self):
        for e in (self._key_ready, self._init_received, self._photons_received, self._bases_received, self._matches_received): e.clear()
        self._received_photons_data = self._received_bases = self._received_matches = None
        self._received_key = self._received_error_rate = None

    def _display_basis_comparison(self, alice_bases, bob_bases, num):
        table = Table(box=box.SIMPLE, show_header=True, header_style="dim", padding=(0, 1))
        table.add_column("Pos", justify="center", width=4); table.add_column("A", justify="center", width=5)
        table.add_column("B", justify="center", width=5); table.add_column("", justify="center", width=3)
        for i in range(min(16, num)):
            a = '- |' if alice_bases[i] == RECTILINEAR else '/ \\'
            b = '- |' if bob_bases[i] == RECTILINEAR else '/ \\'
            match = alice_bases[i] == bob_bases[i]
            table.add_row(str(i+1), a, b, "[green]✓[/]" if match else "[red]✗[/]")
        self.console.print(table)

    def _prompt_bits(self, count):
        print(f"\n  {self.role} [bits] > ", end='', flush=True)
        chars = []
        while len(chars) < count:
            try: ch = _getch()
            except KeyboardInterrupt: print(); return None
            if ch in ('\x03',): print(); return None
            elif ch in ('\b', '\x7f'):
                if chars: chars.pop(); print('\b \b', end='', flush=True)
            elif ch in ('0', '1'): chars.append(ch); print(ch, end='', flush=True)
        print()
        self.console.print(f"  [dim]Bits:[/dim] {' '.join(chars)}")
        return [int(c) for c in chars]

    def _prompt_bases(self, count):
        valid = {'-', '|', '/', '\\'}
        print(f"\n  {self.role} [bases] > ", end='', flush=True)
        chars = []
        while len(chars) < count:
            try: ch = _getch()
            except KeyboardInterrupt: print(); return None
            if ch in ('\x03',): print(); return None
            elif ch in ('\b', '\x7f'):
                if chars: chars.pop(); print('\b \b', end='', flush=True)
            elif ch in valid: chars.append(ch); print(ch, end='', flush=True)
        print()
        self.console.print(f"  [dim]Bases:[/dim] {' '.join(chars)}")
        return chars

    def send_chat_message(self, text):
        if not self.send_key_manager.get_key():
            display_system_message(self.console, "No key! Use /refresh first.", "ERROR"); return
        key = self.send_key_manager.get_key(); bits_needed = len(text) * 8
        if key.remaining() < bits_needed:
            display_system_message(self.console, "Key exhausted! Use /refresh to generate a new key.", "ERROR"); return
        try: ciphertext, details = encrypt_message(text, self.send_key_manager)
        except KeyExhaustedError: display_system_message(self.console, "Key exhausted. Use /refresh.", "ERROR"); return
        if self.verbose: display_encryption(self.console, details, "SENDING")
        msg = Message(sender=self.role, content=text, encrypted=ciphertext, bits_used=details['bits_used'])
        self.history.add_message(msg)
        self.network.send(MSG_CHAT, {'sender': self.role, 'ciphertext': ciphertext, 'bits_used': details['bits_used']})
        display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_sent(len(text.encode('utf-8')))
        display_status_bar(self.console, self.send_key_manager, self.stats)
        key = self.send_key_manager.get_key()
        if key and key.needs_rotation():
            display_system_message(self.console, f"Key usage at {key.usage_percentage():.0f}%. Use /refresh for new key.", "WARNING")

    def handle_received_message(self, msg_type, payload, seq):
        with self._lock:
            if msg_type == MSG_CHAT: self._handle_chat(payload)
            elif msg_type == MSG_BB84_INIT: self._init_received.set()
            elif msg_type == MSG_BB84_PHOTONS:
                self._received_photons_data = payload.get('photons', []); self._photons_received.set()
            elif msg_type == MSG_BB84_BASES:
                self._received_bases = payload.get('bases', []); self._bases_received.set()
            elif msg_type == MSG_BB84_MATCHES:
                self._received_matches = payload.get('positions', []); self._matches_received.set()
            elif msg_type == MSG_BB84_COMPLETE: self._handle_key_sync(payload)
            elif msg_type == MSG_EVE_TOGGLE:
                display_system_message(self.console, f"Peer toggled Eve: {'enabled' if payload.get('active') else 'disabled'}", "INFO")
            elif msg_type == MSG_DISCONNECT:
                display_system_message(self.console, "Peer disconnected.", "WARNING"); self.running = False
            elif msg_type == MSG_KEY_ROTATE:
                display_system_message(self.console, "Peer is starting new key exchange...", "INFO")
                if self.role == "Bob": self._clear_exchange_state()

    def _handle_chat(self, payload):
        ciphertext = payload['ciphertext']; sender = payload.get('sender', self.peer)
        if not self.recv_key_manager.get_key():
            display_system_message(self.console, "Received message but no key!", "ERROR"); return
        try: plaintext, details = decrypt_message(ciphertext, self.recv_key_manager)
        except KeyExhaustedError: display_system_message(self.console, "Key exhausted during decrypt!", "ERROR"); return
        if self.verbose: display_decryption(self.console, details)
        msg = Message(sender=sender, content=plaintext, encrypted=ciphertext, bits_used=payload.get('bits_used', 0))
        self.history.add_message(msg); display_message(self.console, msg, show_encrypted=True)
        self.stats.record_message_received(len(plaintext.encode('utf-8')))
        display_status_bar(self.console, self.recv_key_manager, self.stats)

    def _handle_key_sync(self, payload):
        key_bits = payload.get('key', []); error_rate = payload.get('error_rate', 0.0)
        if key_bits:
            self._received_key = key_bits; self._received_error_rate = error_rate
            if not self._photons_received.is_set():
                self.send_key_manager.set_key(list(key_bits), error_rate)
                self.recv_key_manager.set_key(list(key_bits), error_rate)
                display_system_message(self.console, f"Secure key received from peer: {len(key_bits)} bits", "SUCCESS")
            self._key_ready.set()

    def process_command(self, cmd):
        parts = cmd.strip().split(); command = parts[0].lower(); args = parts[1:] if len(parts) > 1 else []
        if command == '/help': display_help(self.console)
        elif command == '/key': display_key_info(self.console, self.send_key_manager)
        elif command == '/refresh':
            self.stats.record_manual_rotation()
            try: self.network.send(MSG_KEY_ROTATE, {})
            except: pass
            if self.role == "Alice": self.interactive_key_exchange_alice()
            else: self.interactive_key_exchange_bob()
        elif command == '/stats': display_stats(self.console, self.stats, self.send_key_manager, self.role, self.peer_address)
        elif command == '/verbose':
            if args and args[0].lower() == 'on': self.verbose = True; display_system_message(self.console, "Verbose mode enabled.", "INFO")
            elif args and args[0].lower() == 'off': self.verbose = False; display_system_message(self.console, "Verbose mode disabled.", "INFO")
            else: display_system_message(self.console, f"Verbose is {'ON' if self.verbose else 'OFF'}. Use /verbose on or /verbose off.", "INFO")
        elif command == '/clear':
            self.console.clear(); display_header(self.console, self.role, self.peer, self.send_key_manager, self.stats)
        elif command == '/history': display_chat_history(self.console, self.history, show_encrypted=True)
        elif command == '/export':
            filename = f"chat_transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.history.export(filename); display_system_message(self.console, f"Transcript exported to {filename}", "SUCCESS")
        elif command == '/eve':
            self.stats.eve_active = not self.stats.eve_active
            state = "enabled" if self.stats.eve_active else "disabled"
            display_system_message(self.console, f"Eve simulation is now {state}.", "WARNING")
            try: self.network.send(MSG_EVE_TOGGLE, {'active': self.stats.eve_active})
            except: pass
        elif command == '/quit':
            display_system_message(self.console, "Disconnecting...", "INFO")
            try: self.network.send(MSG_DISCONNECT, {})
            except: pass
            self.running = False; return False
        else: display_system_message(self.console, f"Unknown command: {command}. Type /help.", "ERROR")
        return True

    def run(self):
        display_welcome(self.console, self.role); self.stats.mark_connected()
        self.network.start_receiving(self.handle_received_message)
        if self.role == "Alice": self.interactive_key_exchange_alice()
        else: self.interactive_key_exchange_bob()
        display_header(self.console, self.role, self.peer, self.send_key_manager, self.stats)
        display_status_bar(self.console, self.send_key_manager, self.stats)
        while self.running:
            try:
                user_input = input(f"\n  {self.role} > ").strip()
                if not user_input: continue
                if user_input.startswith('/'): 
                    if not self.process_command(user_input): break
                else: self.send_chat_message(user_input)
            except (KeyboardInterrupt, EOFError):
                self.console.print(); display_system_message(self.console, "Disconnecting...", "INFO")
                try: self.network.send(MSG_DISCONNECT, {})
                except: pass
                break
        self.cleanup()

    def cleanup(self):
        self.send_key_manager.clear(); self.recv_key_manager.clear()
        self.network.stop(); display_system_message(self.console, "Keys cleared from memory. Goodbye!", "SUCCESS")

# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════
def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close(); return ip
    except: return "127.0.0.1"

def main():
    console = create_console()
    console.print()
    console.print("[bold bright_cyan]╔══════════════════════════════════════════════╗[/]")
    console.print("[bold bright_cyan]║[/]  [bold bright_white]BB84 QUANTUM SECURE CHAT[/]                   [bold bright_cyan]║[/]")
    console.print("[bold bright_cyan]║[/]  [dim]Quantum Key Distribution • XOR Encryption[/] [bold bright_cyan]║[/]")
    console.print("[bold bright_cyan]╚══════════════════════════════════════════════╝[/]")
    console.print()

    # Role selection
    console.print("[bold]Who do you want to be?[/]")
    console.print("  [bold cyan]1.[/] Alice (connects to Bob)")
    console.print("  [bold green]2.[/] Bob   (waits for Alice)")
    console.print()
    choice = input("  Choose [1/2]: ").strip()

    if choice == '2' or choice.lower().startswith('b'):
        # ── Bob (Server) ──
        lan_ip = get_lan_ip()
        console.print()
        console.print(f"  [bold green]Your IP:[/] [bold bright_white]{lan_ip}[/]")
        console.print(f"  [dim]Tell Alice to enter this IP when prompted.[/dim]")
        console.print()

        server = Server(host='0.0.0.0', port=PORT)
        display_system_message(console, f"Starting server on 0.0.0.0:{PORT}...", "INFO")
        server.start()
        display_system_message(console, f"Waiting for Alice to connect...", "INFO")

        try:
            client_address = server.accept_connection()
            display_system_message(console, f"Alice connected from {client_address}!", "SUCCESS")
        except KeyboardInterrupt:
            display_system_message(console, "Server interrupted.", "WARNING")
            server.stop(); sys.exit(0)

        chat = ChatManager(role="Bob", network=server)
        chat.peer_address = f"{client_address[0]}:{client_address[1]}"
        try: chat.run()
        except Exception as e: display_system_message(console, f"Fatal error: {e}", "ERROR")
        finally: server.stop()

    else:
        # ── Alice (Client) ──
        console.print()
        host = input("  Enter Bob's IP (or press Enter for localhost): ").strip()
        if not host: host = 'localhost'

        client = Client(host=host, port=PORT)
        display_system_message(console, f"Connecting to Bob at {host}:{PORT}...", "INFO")

        if not client.connect():
            display_system_message(console, "Failed to connect to Bob. Is the server running?", "ERROR")
            sys.exit(1)

        display_system_message(console, f"Connected to Bob at {host}:{PORT}!", "SUCCESS")
        chat = ChatManager(role="Alice", network=client)
        chat.peer_address = f"{host}:{PORT}"
        try: chat.run()
        except Exception as e: display_system_message(console, f"Fatal error: {e}", "ERROR")
        finally: client.stop()


if __name__ == '__main__':
    main()
