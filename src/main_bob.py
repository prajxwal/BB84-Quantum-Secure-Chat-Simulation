"""
BB84 Quantum Secure Chat - Bob (Server)
Entry point for Bob, who hosts the server and waits for Alice.

Usage:
    python -m src.main_bob [--host HOST] [--port PORT]
"""

import sys
import os
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import HOST, PORT
from src.network.server import Server
from src.chat.manager import ChatManager


def main():
    parser = argparse.ArgumentParser(description="BB84 Quantum Chat - Bob (Server)")
    parser.add_argument('--host', default=HOST, help=f"Bind host (default: {HOST})")
    parser.add_argument('--port', type=int, default=PORT, help=f"Bind port (default: {PORT})")
    args = parser.parse_args()

    # Create server
    server = Server(host=args.host, port=args.port)

    # Create console for connection messages
    from src.ui.interface import create_console, display_system_message
    console = create_console()

    display_system_message(console, f"Starting server on {args.host}:{args.port}...", "INFO")
    server.start()
    display_system_message(console, f"Waiting for Alice to connect...", "INFO")

    try:
        client_address = server.accept_connection()
        display_system_message(console, f"Alice connected from {client_address}!", "SUCCESS")
    except KeyboardInterrupt:
        display_system_message(console, "Server interrupted.", "WARNING")
        server.stop()
        sys.exit(0)

    # Create and run chat manager
    chat = ChatManager(role="Bob", network=server)
    chat.peer_address = f"{client_address[0]}:{client_address[1]}"

    try:
        chat.run()
    except Exception as e:
        display_system_message(console, f"Fatal error: {e}", "ERROR")
    finally:
        server.stop()


if __name__ == '__main__':
    main()
