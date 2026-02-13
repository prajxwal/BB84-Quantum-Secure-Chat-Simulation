"""
BB84 Quantum Chat - BB84 Key Exchange Visualization
Renders the 7-phase key exchange process with progress bars and tables.
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, SpinnerColumn
from rich.text import Text
from rich import box

from config.constants import BASIS_SYMBOLS, ANGLE_SYMBOLS
from config.settings import ANIMATION_SPEED
from src.ui.colors import COLORS, SYMBOLS


def display_bb84_exchange(console: Console, result: dict, animate: bool = True):
    """Display the full BB84 key exchange visualization."""
    delay = ANIMATION_SPEED if animate else 0
    num_photons = len(result['alice_bits'])

    console.print()
    console.print(Panel(
        "[bold bright_cyan]BB84 QUANTUM KEY DISTRIBUTION PROTOCOL[/]",
        box=box.DOUBLE,
        style="bright_cyan",
        expand=True,
    ))
    console.print()

    # ── Phase 1: Alice generates random bits ────────────────────
    _phase_header(console, 1, 7, "Alice generating random bits...")
    _animate_progress(console, delay)

    bits_display = ' '.join(str(b) for b in result['alice_bits'][:16])
    console.print(f"  Generated: [bold]{num_photons}[/] bits")
    console.print(f"  Sample:    [bright_white]{bits_display}[/] ...")
    console.print()
    _separator(console)

    # ── Phase 2: Alice selects random bases ─────────────────────
    _phase_header(console, 2, 7, "Alice selecting random bases...")
    _animate_progress(console, delay)

    bases_display = ' '.join(BASIS_SYMBOLS[b] for b in result['alice_bases'][:16])
    console.print(f"  Bases:     [bright_magenta]{bases_display}[/] ...")
    console.print()
    _separator(console)

    # ── Phase 3: Encoding photons ───────────────────────────────
    _phase_header(console, 3, 7, "Encoding photons with polarization...")
    _animate_progress(console, delay)

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_cyan")
    table.add_column("Pos", justify="center", width=6)
    table.add_column("Bit", justify="center", width=6)
    table.add_column("Basis", justify="center", width=8)
    table.add_column("Polarization", justify="center", width=18)

    photons = result['photons']
    show_count = min(8, len(photons))
    for i in range(show_count):
        p = photons[i]
        angle_sym = ANGLE_SYMBOLS.get(p.angle, '?')
        table.add_row(
            str(i + 1),
            f"[bright_white]{p.bit}[/]",
            f"[bright_magenta]{BASIS_SYMBOLS[p.basis]}[/]",
            f"[bright_yellow]{p.angle}° ({angle_sym})[/]",
        )
    if len(photons) > show_count:
        table.add_row("...", "...", "...", "...")

    console.print(table)
    console.print()
    _separator(console)

    # ── Phase 4: Transmitting photons ───────────────────────────
    _phase_header(console, 4, 7, "Transmitting photons ~~~> Bob")
    _animate_progress(console, delay)

    photon_line = "  Alice  "
    for i in range(min(6, show_count)):
        p = photons[i]
        photon_line += f"[bright_yellow]~~~>  [/]"
    photon_line += " Bob"
    console.print(photon_line)

    angle_line = "          "
    for i in range(min(6, show_count)):
        p = photons[i]
        angle_sym = ANGLE_SYMBOLS.get(p.angle, '?')
        angle_line += f"[bright_magenta]{angle_sym}     [/]"
    console.print(angle_line)
    console.print()

    if result.get('eve_active'):
        console.print(f"  [bold red]{SYMBOLS['warning']} EVE INTERCEPTED THE QUANTUM CHANNEL![/]")
        console.print()

    _separator(console)

    # ── Phase 5: Bob measures photons ───────────────────────────
    _phase_header(console, 5, 7, "Bob measuring photons with random bases...")
    _animate_progress(console, delay)

    bob_bases_display = ' '.join(BASIS_SYMBOLS[b] for b in result['bob_bases'][:16])
    console.print(f"  Bob's random bases: [bright_magenta]{bob_bases_display}[/] ...")
    console.print()

    cmp_table = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_cyan")
    cmp_table.add_column("Pos", justify="center", width=6)
    cmp_table.add_column("Alice Basis", justify="center", width=12)
    cmp_table.add_column("Bob Basis", justify="center", width=12)
    cmp_table.add_column("Match?", justify="center", width=8)

    for i in range(show_count):
        a_basis = BASIS_SYMBOLS[result['alice_bases'][i]]
        b_basis = BASIS_SYMBOLS[result['bob_bases'][i]]
        match = result['alice_bases'][i] == result['bob_bases'][i]
        match_sym = f"[green]{SYMBOLS['check']}[/]" if match else f"[red]{SYMBOLS['cross']}[/]"
        cmp_table.add_row(str(i + 1), a_basis, b_basis, match_sym)
    if num_photons > show_count:
        cmp_table.add_row("...", "...", "...", "...")

    console.print(cmp_table)
    console.print()
    _separator(console)

    # ── Phase 6: Basis reconciliation ───────────────────────────
    _phase_header(console, 6, 7, "Basis reconciliation...")
    _animate_progress(console, delay)

    matching = result['matching_positions']
    match_display = ', '.join(str(p + 1) for p in matching[:12])
    if len(matching) > 12:
        match_display += '...'
    match_rate = result['match_rate']

    console.print("  Comparing bases (public channel)...")
    console.print(f"  Matching positions: [green]{match_display}[/]")
    console.print(f"  Match rate: [bold]{match_rate:.1%}[/] ({len(matching)}/{num_photons} bits)")
    console.print()
    console.print("  Extracting shared key from matching positions...")
    console.print()
    _separator(console)

    # ── Phase 7: Error checking ─────────────────────────────────
    _phase_header(console, 7, 7, "Privacy amplification & error checking...")
    _animate_progress(console, delay)

    error_rate = result['error_rate']
    sample_size = len(result['sample_positions'])
    errors = sum(a != b for a, b in zip(result['alice_sample'], result['bob_sample']))

    console.print(f"  Sampling {len(result['sample_positions'])} bits for eavesdropper detection...")
    console.print(f"  Comparing sample bits between Alice and Bob...")
    console.print()
    console.print(f"  Error rate: [bold]{error_rate:.1%}[/] ({errors}/{sample_size} bits differ)")
    console.print()

    # Final result box
    final_len = result['final_key_length']
    eavesdropped = result.get('eavesdropper_detected', False)

    if eavesdropped:
        _display_eavesdropper_alert(console, error_rate)
    else:
        from src.crypto.utils import key_to_hex
        key_hex = key_to_hex(result['alice_final_key'][:64])
        status_sym = SYMBOLS['secure']
        status_text = "SECURE"
        status_style = "bold green"

        summary = Text()
        summary.append("\n")
        summary.append(f"            {SYMBOLS['check']} SECURE KEY ESTABLISHED\n\n", style="bold green")
        summary.append(f"  Final Key Length:    {final_len} bits\n")
        summary.append(f"  Error Rate:          {error_rate:.1%}\n")
        summary.append(f"  Security Status:     {status_sym} {status_text}\n", style=status_style)
        summary.append(f"\n  Key (hex):          {key_hex}\n")

        console.print(Panel(summary, box=box.DOUBLE, style="green", title="[bold]KEY EXCHANGE COMPLETE[/]"))

    console.print()


def _display_eavesdropper_alert(console: Console, error_rate: float):
    """Display eavesdropper detection alert box."""
    from config.settings import ERROR_THRESHOLD
    alert = Text()
    alert.append("\n")
    alert.append(f"            {SYMBOLS['warning']} EAVESDROPPER DETECTED!\n\n", style="bold red")
    alert.append(f"  The quantum channel has been compromised.\n")
    alert.append(f"  Error rate ({error_rate:.1%}) exceeds security threshold ({ERROR_THRESHOLD:.1%}).\n\n")
    alert.append(f"  Actions taken:\n")
    alert.append(f"    • Current key discarded\n")
    alert.append(f"    • Initiating new key exchange...\n")

    console.print(Panel(alert, box=box.DOUBLE, style="red", title="[bold red]SECURITY ALERT[/]"))


def _phase_header(console: Console, phase: int, total: int, description: str):
    """Print a phase header."""
    console.print(f"  [bold bright_cyan][PHASE {phase}/{total}][/] {description}")


def _animate_progress(console: Console, delay: float):
    """Show a quick progress bar animation."""
    if delay <= 0:
        return
    with Progress(
        SpinnerColumn(),
        BarColumn(bar_width=50),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("", total=100)
        for i in range(100):
            progress.update(task, advance=1)
            time.sleep(delay * 0.3)


def _separator(console: Console):
    """Print a separator line."""
    console.print("[dim]" + "─" * 65 + "[/]")
    console.print()
