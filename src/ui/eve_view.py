"""
BB84 Quantum Chat - Eavesdropper Detection View
Renders the Eve interception analysis and detection screen.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config.constants import BASIS_SYMBOLS
from config.settings import ERROR_THRESHOLD
from src.ui.colors import SYMBOLS


def display_eve_analysis(console: Console, result: dict):
    """Display the eavesdropper analysis screen."""
    if not result.get('eve_active') or result.get('eve_bits') is None:
        return

    console.print()
    console.print(Panel(
        f"[bold red]{SYMBOLS['warning']} WARNING: Eve has intercepted the quantum channel![/]",
        box=box.DOUBLE,
        style="red",
        expand=True,
    ))

    # Interception table
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold red",
        title="[bold]Interception Analysis[/]",
    )
    table.add_column("Pos", justify="center", width=6)
    table.add_column("Alice Sent", justify="center", width=10)
    table.add_column("Eve Measured", justify="center", width=12)
    table.add_column("Bob Received", justify="center", width=12)
    table.add_column("Alice vs Bob", justify="center", width=12)
    table.add_column("Status", justify="center", width=10)

    alice_bits = result['alice_bits']
    eve_bits = result.get('eve_bits', [])
    bob_bits = result['bob_bits']
    matching_pos = set(result['matching_positions'])

    show_count = min(10, len(alice_bits))
    for i in range(show_count):
        if i not in matching_pos:
            continue
        a = alice_bits[i]
        e = eve_bits[i] if i < len(eve_bits) else '?'
        b = bob_bits[i]
        match = a == b
        match_text = "Match" if match else "ERROR"
        match_style = "green" if match else "bold red"
        status = f"[green]{SYMBOLS['check']}[/]" if match else f"[red]{SYMBOLS['warning']} DIFF[/]"

        table.add_row(
            str(i + 1),
            str(a),
            str(e),
            str(b),
            f"[{match_style}]{match_text}[/]",
            status,
        )

    if len(alice_bits) > show_count:
        table.add_row("...", "...", "...", "...", "...", "...")

    console.print(table)
    console.print()

    # Error statistics
    error_rate = result['error_rate']
    sample_pos = result['sample_positions']
    alice_sample = result['alice_sample']
    bob_sample = result['bob_sample']
    errors = sum(a != b for a, b in zip(alice_sample, bob_sample))
    total = len(sample_pos)

    stats_text = Text()
    stats_text.append(f"\n  Total bits compared:     {total}\n")
    stats_text.append(f"  Matching bits:           {total - errors}\n")
    stats_text.append(f"  Mismatched bits:         {errors}\n")
    stats_text.append(f"  Error rate:              {error_rate:.1%}\n\n")
    stats_text.append(f"  Threshold:               {ERROR_THRESHOLD:.1%}\n")

    exceeded = error_rate > ERROR_THRESHOLD
    if exceeded:
        stats_text.append(f"  Status:                  {SYMBOLS['compromised']} THRESHOLD EXCEEDED\n",
                          style="bold red")
    else:
        stats_text.append(f"  Status:                  {SYMBOLS['secure']} Below threshold\n",
                          style="bold green")

    console.print(Panel(stats_text, title="[bold]Error Statistics[/]", box=box.ROUNDED))
    console.print()
