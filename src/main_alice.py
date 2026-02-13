"""
BB84 Quantum Secure Chat - Alice (Client)
Entry point for Alice, who connects to Bob's server.

Usage:
    python -m src.main_alice [--host HOST] [--port PORT]
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import HOST, PORT
from src.network.client import Client
from src.chat.manager import ChatManager


def main():
    parser = argparse.ArgumentParser(description="BB84 Quantum Chat - Alice (Client)")
    parser.add_argument('--host', default=HOST, help=f"Server host (default: {HOST})")
    parser.add_argument('--port', type=int, default=PORT, help=f"Server port (default: {PORT})")
    args = parser.parse_args()

    # Create client
    client = Client(host=args.host, port=args.port)

    # Create console for connection messages
    from src.ui.interface import create_console, display_system_message
    console = create_console()

    display_system_message(console, f"Connecting to Bob at {args.host}:{args.port}...", "INFO")

    if not client.connect():
        display_system_message(console, "Failed to connect to Bob. Is the server running?", "ERROR")
        sys.exit(1)

    display_system_message(console, f"Connected to Bob at {args.host}:{args.port}!", "SUCCESS")

    # Create and run chat manager
    chat = ChatManager(role="Alice", network=client)
    chat.peer_address = f"{args.host}:{args.port}"

    try:
        chat.run()
    except Exception as e:
        display_system_message(console, f"Fatal error: {e}", "ERROR")
    finally:
        client.stop()


if __name__ == '__main__':
    main()
