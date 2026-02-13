"""
BB84 Quantum Chat - Encryption Visualization
Shows the step-by-step encryption/decryption process.
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from src.crypto.utils import bits_to_string


def display_encryption(console: Console, details: dict, direction: str = "SENDING"):
    """Display the encryption visualization."""
    msg = details['message']
    msg_bits = details['message_bits']
    key_bits = details['key_bits']
    cipher_bits = details['cipher_bits']
    ciphertext = details['ciphertext_hex']
    bits_used = details['bits_used']

    content = Text()
    content.append(f"\n  Original Message:\n", style="bold")
    content.append(f'  "{msg}"\n\n')

    content.append("  " + "─" * 55 + "\n\n")

    # Step 1: Text to binary
    content.append("  Step 1: Convert to Binary\n\n", style="bold bright_cyan")
    chars = list(msg[:10])
    char_line = "  "
    for c in chars:
        char_line += f"{c:<9}"
    content.append(char_line + "\n")
    content.append(f"  {bits_to_string(msg_bits[:80])}\n\n")

    content.append("  " + "─" * 55 + "\n\n")

    # Step 2: XOR with key
    content.append("  Step 2: Apply BB84 Key (XOR Operation)\n\n", style="bold bright_cyan")
    content.append(f"  Message:  {bits_to_string(msg_bits[:40])} ...\n")
    content.append(f"  Key:      {bits_to_string(key_bits[:40])} ...\n")
    content.append(f"            {'⊕        ' * 5}\n")
    content.append(f"  Result:   {bits_to_string(cipher_bits[:40])} ...\n\n")

    content.append("  " + "─" * 55 + "\n\n")

    # Step 3: Binary to hex
    content.append("  Step 3: Convert to Hexadecimal\n\n", style="bold bright_cyan")
    content.append(f"  Ciphertext: [bold magenta]{ciphertext}[/]\n\n")

    content.append("  " + "─" * 55 + "\n\n")
    content.append(f"  [bold green][TRANSMITTED] ~~~>[/]\n\n")
    content.append(f"  Key bits consumed: {bits_used}\n")

    title = f"[bold]{direction} MESSAGE[/]"
    console.print(Panel(content, box=box.ROUNDED, title=title, style="bright_cyan"))


def display_decryption(console: Console, details: dict):
    """Display brief decryption info."""
    ciphertext = details['ciphertext_hex']
    plaintext = details['plaintext']
    bits_used = details['bits_used']

    content = Text()
    content.append(f"  Ciphertext: [dim]{ciphertext}[/]\n")
    content.append(f"  Decrypted:  [bold green]{plaintext}[/]\n")
    content.append(f"  Key bits:   {bits_used}\n")

    console.print(Panel(content, box=box.ROUNDED, title="[bold]DECRYPTING MESSAGE[/]", style="green"))
