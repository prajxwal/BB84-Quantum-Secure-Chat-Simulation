"""
BB84 Quantum Chat - Help Screen
Displays commands, examples, and BB84 explanation.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box


def display_help(console: Console):
    """Display the help screen."""
    console.print()
    console.print(Panel(
        "[bold bright_white]BB84 QUANTUM CHAT - HELP[/]",
        box=box.DOUBLE,
        style="bright_cyan",
        expand=True,
    ))

    # Commands
    cmds = Text()
    cmds.append("\n")
    cmds.append("  /help                   Show this help menu\n\n", style="bold")
    cmds.append("  /key                    Display current encryption key\n")
    cmds.append("                          • Shows key in binary and hexadecimal\n")
    cmds.append("                          • Displays key length and usage stats\n\n")
    cmds.append("  /refresh                Generate new BB84 key\n")
    cmds.append("                          • Initiates new quantum key exchange\n")
    cmds.append("                          • Seamlessly transitions to new key\n\n")
    cmds.append("  /stats                  Show detailed statistics\n")
    cmds.append("                          • Connection, messages, key, security\n\n")
    cmds.append("  /eve [on|off]           Simulate eavesdropper attack\n")
    cmds.append("                          • on:  Enable Eve to intercept photons\n")
    cmds.append("                          • off: Disable eavesdropper simulation\n\n")
    cmds.append("  /verbose [on|off]       Toggle encryption visualization\n")
    cmds.append("                          • on:  Show detailed encrypt/decrypt steps\n")
    cmds.append("                          • off: Show only final ciphertext\n\n")
    cmds.append("  /clear                  Clear chat history from screen\n\n")
    cmds.append("  /history                Show complete message history\n\n")
    cmds.append("  /export                 Export chat transcript to file\n\n")
    cmds.append("  /quit                   Exit the chat application\n")

    console.print(Panel(cmds, title="[bold]AVAILABLE COMMANDS[/]", box=box.ROUNDED))

    # Keyboard shortcuts
    keys = Text()
    keys.append("\n")
    keys.append("  Ctrl+C                  Exit application (same as /quit)\n")
    keys.append("  Ctrl+L                  Clear screen (same as /clear)\n")

    console.print(Panel(keys, title="[bold]KEYBOARD SHORTCUTS[/]", box=box.ROUNDED))

    # About BB84
    about = Text()
    about.append("\n")
    about.append("  BB84 (Bennett-Brassard 1984) is a quantum key distribution\n")
    about.append("  protocol that uses quantum mechanics to establish a shared\n")
    about.append("  secret key between two parties. The security is guaranteed by\n")
    about.append("  the laws of physics — any eavesdropping attempt will disturb\n")
    about.append("  the quantum states and be detected.\n\n")
    about.append("  This application simulates the BB84 protocol to demonstrate\n")
    about.append("  quantum-secure communication.\n")

    console.print(Panel(about, title="[bold]ABOUT BB84[/]", box=box.ROUNDED))
    console.print()
