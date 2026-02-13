"""
BB84 Quantum Chat - Statistics View
Renders the comprehensive statistics panel.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from src.stats.collector import Statistics
from src.crypto.key_manager import KeyManager
from src.ui.colors import SYMBOLS


def display_stats(console: Console, stats: Statistics, key_manager: KeyManager,
                  role: str, peer_address: str = ""):
    """Display the full statistics panel."""
    console.print()
    console.print(Panel(
        "[bold bright_white]QUANTUM CHANNEL STATISTICS[/]",
        box=box.DOUBLE,
        style="bright_cyan",
        expand=True,
    ))

    # ── Connection ──────────────────────────────────────────────
    sec_status = stats.security_status()
    sec_sym = SYMBOLS['secure'] if sec_status == "SECURE" else SYMBOLS['compromised']
    sec_style = "green" if sec_status == "SECURE" else "red"

    conn_text = Text()
    conn_text.append(f"  Connection Status:     {sec_sym} ACTIVE\n")
    conn_text.append(f"  Role:                  {role}\n")
    if peer_address:
        conn_text.append(f"  Connected To:          {peer_address}\n")
    conn_text.append(f"  Connection Time:       {stats.uptime_str()}\n")
    conn_text.append(f"  Reconnections:         {stats.reconnection_count}\n")

    console.print(Panel(conn_text, title="[bold]CONNECTION[/]", box=box.ROUNDED))

    # ── Messages ────────────────────────────────────────────────
    msg_text = Text()
    msg_text.append(f"  Messages Sent:         {stats.messages_sent}\n")
    msg_text.append(f"  Messages Received:     {stats.messages_received}\n")
    msg_text.append(f"  Total Messages:        {stats.total_messages()}\n\n")
    msg_text.append(f"  Data Encrypted:        {stats.data_encrypted} B\n")
    msg_text.append(f"  Data Decrypted:        {stats.data_decrypted} B\n")
    msg_text.append(f"  Total Data:            {stats.total_data_str()}\n")

    console.print(Panel(msg_text, title="[bold]MESSAGES[/]", box=box.ROUNDED))

    # ── Current Key ─────────────────────────────────────────────
    key = key_manager.get_key()
    key_text = Text()
    if key:
        usage_pct = key.usage_percentage()
        bar_len = 40
        filled = int(bar_len * usage_pct / 100)
        bar = '█' * filled + '░' * (bar_len - filled)

        key_text.append(f"  Key Length:            {key.length} bits\n")
        key_text.append(f"  Key Generated:         {int(key.age_seconds())} seconds ago\n")
        key_text.append(f"  Key ID:                #{key.id}\n\n")
        key_text.append(f"  Usage:\n")
        key_text.append(f"    Bits Used:           {key.bits_used} / {key.length} ({usage_pct:.0f}%)\n")
        key_text.append(f"    Bits Remaining:      {key.remaining()}\n")
        key_text.append(f"    [{bar}]\n\n")

        if key.needs_rotation():
            key_text.append(f"  Status:                ⚠️  Rotation recommended\n")
        else:
            key_text.append(f"  Status:                {SYMBOLS['secure']} Healthy\n")
    else:
        key_text.append("  No key established yet.\n")

    console.print(Panel(key_text, title="[bold]CURRENT KEY[/]", box=box.ROUNDED))

    # ── BB84 Protocol ───────────────────────────────────────────
    bb84_text = Text()
    bb84_text.append(f"  Total Key Exchanges:   {stats.exchange_count}\n")
    bb84_text.append(f"  Successful:            {stats.exchange_count - stats.keys_compromised}\n")
    bb84_text.append(f"  Compromised:           {stats.keys_compromised}\n\n")

    if stats.exchange_count > 0:
        bb84_text.append(f"  Last Exchange:\n")
        bb84_text.append(f"    Photons Sent:        {stats.total_photons_sent // max(1, stats.exchange_count)}\n")
        bb84_text.append(f"    Basis Matches:       {stats.last_match_rate:.1%}\n")
        bb84_text.append(f"    Final Key Length:     {stats.last_key_length} bits\n")
        bb84_text.append(f"    Error Rate:          {stats.last_error_rate:.1%}\n")
        bb84_text.append(f"    Duration:            {stats.last_exchange_duration:.1f}s\n\n")
        bb84_text.append(f"  Averages:\n")
        bb84_text.append(f"    Match Rate:          {stats.avg_match_rate():.1%}\n")
        bb84_text.append(f"    Error Rate:          {stats.avg_error_rate():.1%}\n")
        bb84_text.append(f"    Duration:            {stats.avg_duration():.1f}s\n")

    console.print(Panel(bb84_text, title="[bold]BB84 PROTOCOL[/]", box=box.ROUNDED))

    # ── Security ────────────────────────────────────────────────
    sec_text = Text()
    sec_text.append(f"  Security Status:       {sec_sym} {sec_status}\n", style=sec_style)
    sec_text.append(f"  Eve Simulation:        {'ACTIVE' if stats.eve_active else 'Disabled'}\n")
    sec_text.append(f"  Error Rate:            {stats.last_error_rate:.1%}\n")
    sec_text.append(f"  Threshold:             10.0%\n\n")
    sec_text.append(f"  Security Events:\n")
    sec_text.append(f"    Eavesdropper Detected:    {stats.eavesdropper_detected_count}\n")
    sec_text.append(f"    Keys Compromised:         {stats.keys_compromised}\n")
    sec_text.append(f"    Auto Key Rotations:       {stats.auto_rotations}\n")
    sec_text.append(f"    Manual Key Rotations:     {stats.manual_rotations}\n")

    console.print(Panel(sec_text, title="[bold]SECURITY[/]", box=box.ROUNDED))
    console.print()
