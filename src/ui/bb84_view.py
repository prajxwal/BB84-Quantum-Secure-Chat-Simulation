"""
BB84 Quantum Chat - BB84 Key Exchange Visualization
Compact IRC-style display for the BB84 key exchange.
"""

import time
from typing import List
from rich.console import Console
from rich.table import Table
from rich import box

from config.constants import BASIS_SYMBOLS, ANGLE_SYMBOLS, BIT_BASIS_TO_SYMBOL
from config.settings import ANIMATION_SPEED
from src.ui.colors import SYMBOLS


def display_bb84_interactive_result(console: Console, final_key: List[int],
                                     error_rate: float, match_rate: float,
                                     num_photons: int):
    """Display the result of an interactive BB84 key exchange."""
    console.print()

    if len(final_key) < 1:
        console.print(f"[bold red]╔══ ⚠  KEY EXCHANGE FAILED ══╗[/]")
        console.print(f"[bold red]║[/] No shared key could be established")
        console.print(f"[bold red]║[/] Try again with /refresh")
        console.print(f"[bold red]╚═══════════════════════════════════╝[/]")
    else:
        from src.crypto.utils import key_to_hex
        from src.crypto.key_manager import EXPANDED_KEY_BITS
        key_hex = key_to_hex(final_key[:64])
        seed_len = len(final_key)

        console.print(f"[bold green]╔══ 🟢 SECURE KEY ESTABLISHED ══╗[/]")
        console.print(f"[bold green]║[/] Length: {seed_len} bits → {EXPANDED_KEY_BITS}b expanded │ Error: {error_rate:.1%}")
        console.print(f"[bold green]║[/] Key: [dim]{key_hex}[/]")
        console.print(f"[bold green]╚═══════════════════════════════════╝[/]")

    console.print()


def display_bb84_exchange(console: Console, result: dict, animate: bool = True):
    """Display the BB84 key exchange in compact IRC style (non-interactive/legacy)."""
    delay = ANIMATION_SPEED if animate else 0
    num_photons = len(result['alice_bits'])

    console.print()
    console.print("[bold bright_cyan]═══ BB84 Quantum Key Distribution ═══[/]")
    console.print()

    # Phase 1: Alice generates random bits
    _phase(console, 1, "Generating random bits...", delay)
    bits_sample = ' '.join(str(b) for b in result['alice_bits'][:16])
    console.print(f"  [dim]{num_photons} bits:[/] {bits_sample} ...")

    # Phase 2: Basis selection
    _phase(console, 2, "Selecting random bases...", delay)
    bases_sample = ' '.join(BASIS_SYMBOLS[b] for b in result['alice_bases'][:16])
    console.print(f"  [dim]Bases:[/] [bright_magenta]{bases_sample}[/] ...")

    # Phase 3: Encoding photons
    _phase(console, 3, "Encoding photons...", delay)
    photons = result['photons']
    polarizations = ' '.join(
        f"{ANGLE_SYMBOLS.get(p.angle, '?')}"
        for p in photons[:12]
    )
    console.print(f"  [dim]Photons:[/] [bright_yellow]{polarizations}[/] ...")

    # Phase 4: Transmission
    _phase(console, 4, "Transmitting photons...", delay)
    console.print(f"  Alice [bright_yellow]~~~> ~~~> ~~~> ~~~> ~~~>[/] Bob")

    if result.get('eve_active'):
        console.print(f"  [bold red]{SYMBOLS['warning']} Eve intercepted the channel![/]")

    # Phase 5: Bob measures
    _phase(console, 5, "Bob measuring photons...", delay)
    bob_bases_sample = ' '.join(BASIS_SYMBOLS[b] for b in result['bob_bases'][:16])
    console.print(f"  [dim]Bob's bases:[/] [bright_magenta]{bob_bases_sample}[/] ...")

    # Show basis comparison table (compact)
    table = Table(box=box.SIMPLE, show_header=True, header_style="dim", padding=(0, 1))
    table.add_column("Pos", justify="center", width=4)
    table.add_column("A", justify="center", width=3)
    table.add_column("B", justify="center", width=3)
    table.add_column("", justify="center", width=3)

    show_count = min(8, num_photons)
    for i in range(show_count):
        a = BASIS_SYMBOLS[result['alice_bases'][i]]
        b = BASIS_SYMBOLS[result['bob_bases'][i]]
        match = result['alice_bases'][i] == result['bob_bases'][i]
        sym = f"[green]✓[/]" if match else f"[red]✗[/]"
        table.add_row(str(i + 1), a, b, sym)

    console.print(table)

    # Phase 6: Reconciliation
    _phase(console, 6, "Basis reconciliation...", delay)
    matching = result['matching_positions']
    match_rate = result['match_rate']
    match_preview = ', '.join(str(p + 1) for p in matching[:10])
    if len(matching) > 10:
        match_preview += '...'

    console.print(f"  [dim]Matching:[/] [green]{match_preview}[/]")
    console.print(f"  [dim]Match rate:[/] {match_rate:.1%} ({len(matching)}/{num_photons})")

    # Phase 7: Error checking
    _phase(console, 7, "Error checking...", delay)
    error_rate = result['error_rate']
    sample_size = len(result['sample_positions'])
    errors = sum(a != b for a, b in zip(result['alice_sample'], result['bob_sample']))

    console.print(f"  [dim]Sampled {sample_size} bits, {errors} errors[/]")
    console.print(f"  [dim]Error rate:[/] {error_rate:.1%}")

    # Final result
    console.print()
    eavesdropped = result.get('eavesdropper_detected', False)

    if eavesdropped:
        console.print(f"[bold red]╔══ {SYMBOLS['warning']} EAVESDROPPER DETECTED ══╗[/]")
        console.print(f"[bold red]║[/] Error rate {error_rate:.1%} > threshold 10.0%")
        console.print(f"[bold red]║[/] Key discarded. Regenerating...")
        console.print(f"[bold red]╚════════════════════════════════════╝[/]")
    else:
        from src.crypto.utils import key_to_hex
        key_hex = key_to_hex(result['alice_final_key'][:64])
        final_len = result['final_key_length']

        console.print(f"[bold green]╔══ {SYMBOLS['secure']} SECURE KEY ESTABLISHED ══╗[/]")
        console.print(f"[bold green]║[/] Length: {final_len} bits │ Error: {error_rate:.1%}")
        console.print(f"[bold green]║[/] Key: [dim]{key_hex}[/]")
        console.print(f"[bold green]╚═══════════════════════════════════╝[/]")

    console.print()


def _phase(console: Console, num: int, description: str, delay: float):
    """Print a phase line with optional delay."""
    console.print(f"  [bold bright_cyan][{num}/7][/] {description}")
    if delay > 0:
        time.sleep(delay * 5)
