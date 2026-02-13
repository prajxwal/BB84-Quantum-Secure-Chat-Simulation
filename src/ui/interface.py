"""
BB84 Quantum Chat - Main UI Controller
Renders the header, chat messages, status bar, and input prompt.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.ui.colors import CHAT_THEME, SYMBOLS
from src.crypto.key_manager import KeyManager
from src.crypto.utils import key_to_hex
from src.stats.collector import Statistics
from src.chat.history import ChatHistory
from src.chat.message import Message


def create_console() -> Console:
    """Create a Rich console with our theme."""
    return Console(theme=CHAT_THEME, highlight=False)


def display_header(console: Console, role: str, peer: str, key_manager: KeyManager,
                   stats: Statistics):
    """Display the top header bar."""
    key = key_manager.get_key()
    key_len = key.length if key else 0
    key_usage = f"{key.usage_percentage():.0f}%" if key else "N/A"
    msg_count = stats.total_messages()
    error_rate = stats.last_error_rate
    sec_status = stats.security_status()
    sec_sym = SYMBOLS['secure'] if sec_status == "SECURE" else SYMBOLS['compromised']

    header = (
        f"     BB84 QUANTUM SECURE CHAT — {role} connected to {peer}\n"
        f"     Key: {key_len} bits ({key_usage} used) | "
        f"Encrypted: {msg_count} msgs | "
        f"Error Rate: {error_rate:.1%} | "
        f"{sec_sym} {sec_status}"
    )

    console.print(Panel(
        f"[bold bright_white]{header}[/]",
        box=box.DOUBLE,
        style="blue",
        expand=True,
    ))


def display_message(console: Console, msg: Message, show_encrypted: bool = True):
    """Display a single chat message."""
    sender_style = "alice" if msg.sender.lower() == "alice" else "bob"
    time_str = msg.time_str()

    console.print(f"  [{sender_style}][{time_str}] {msg.sender}:[/] {msg.content}")
    if show_encrypted and msg.encrypted:
        console.print(f"             [encrypted][ENCRYPTED] {msg.encrypted}[/]")


def display_system_message(console: Console, text: str, level: str = "INFO"):
    """Display a system message."""
    from datetime import datetime
    time_str = datetime.now().strftime('%H:%M:%S')
    style_map = {
        'INFO': 'system',
        'WARNING': 'warning',
        'ERROR': 'error',
        'SUCCESS': 'success',
    }
    style = style_map.get(level, 'system')
    console.print(f"  [{style}][{time_str}] [{level}] {text}[/]")


def display_status_bar(console: Console, key_manager: KeyManager, stats: Statistics):
    """Display the status bar with key usage gauge."""
    key = key_manager.get_key()
    if key:
        usage_pct = key.usage_percentage()
        bar_len = 30
        filled = int(bar_len * usage_pct / 100)
        bar = '█' * filled + '░' * (bar_len - filled)
        rotation_age = int(key.age_seconds())
        age_str = f"{rotation_age // 60} min ago" if rotation_age >= 60 else f"{rotation_age}s ago"

        status = (
            f"[info]Connection secure[/] | Last key rotation: {age_str}\n"
            f"  Key Usage: [{bar}] {usage_pct:.0f}% ({key.bits_used}/{key.length} bits)"
        )
    else:
        status = "[warning]No encryption key established. Use /refresh to generate.[/]"

    console.print(Panel(
        f"  {status}",
        title="[bold]STATUS[/]",
        box=box.ROUNDED,
        style="dim",
    ))


def display_key_info(console: Console, key_manager: KeyManager):
    """Display current key details (/key command)."""
    key = key_manager.get_key()
    if not key:
        display_system_message(console, "No key established. Use /refresh.", "WARNING")
        return

    key_hex = key_to_hex(key.bits[:64])
    key_binary = ' '.join(str(b) for b in key.bits[:32])
    if len(key.bits) > 32:
        key_binary += ' ...'

    text = Text()
    text.append(f"\n  Key ID:       #{key.id}\n")
    text.append(f"  Length:       {key.length} bits\n")
    text.append(f"  Generated:    {int(key.age_seconds())}s ago\n")
    text.append(f"  Error Rate:   {key.error_rate:.1%}\n\n")
    text.append(f"  Binary:       {key_binary}\n")
    text.append(f"  Hex:          {key_hex}\n\n")
    text.append(f"  Used:         {key.bits_used}/{key.length} ({key.usage_percentage():.0f}%)\n")
    text.append(f"  Remaining:    {key.remaining()} bits\n")

    console.print(Panel(text, title="[bold magenta]ENCRYPTION KEY[/]", box=box.ROUNDED, style="magenta"))


def display_chat_history(console: Console, history: ChatHistory, show_encrypted: bool = True):
    """Display all messages in history."""
    messages = history.get_all()
    if not messages:
        console.print("  [dim]No messages yet. Start typing![/]")
        return

    for msg in messages:
        display_message(console, msg, show_encrypted)


def display_welcome(console: Console, role: str):
    """Display the welcome screen."""
    welcome = Text()
    welcome.append("\n")
    welcome.append("  ╔══════════════════════════════════════════════════╗\n", style="bright_cyan")
    welcome.append("  ║                                                  ║\n", style="bright_cyan")
    welcome.append("  ║     BB84 QUANTUM SECURE CHAT                    ║\n", style="bold bright_white")
    welcome.append("  ║                                                  ║\n", style="bright_cyan")
    welcome.append("  ║     Quantum Key Distribution Protocol            ║\n", style="bright_cyan")
    welcome.append("  ║     Secure • Encrypted • Quantum-Safe            ║\n", style="bright_cyan")
    welcome.append("  ║                                                  ║\n", style="bright_cyan")
    welcome.append("  ╚══════════════════════════════════════════════════╝\n", style="bright_cyan")
    welcome.append(f"\n  Running as: [bold]{role}[/]\n")
    welcome.append(f"  Type /help for commands\n\n")

    console.print(welcome)
