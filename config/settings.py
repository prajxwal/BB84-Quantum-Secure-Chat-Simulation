"""
BB84 Quantum Chat - Application Settings
All configurable parameters for the application.
"""

# ─── Network ────────────────────────────────────────────────────
HOST = 'localhost'
PORT = 5000
BUFFER_SIZE = 8192
CONNECTION_TIMEOUT = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF = [1, 2, 4]  # seconds

# ─── BB84 Protocol ──────────────────────────────────────────────
NUM_PHOTONS = 256           # Photons per key exchange (more = longer key)
MIN_KEY_LENGTH = 32         # Minimum acceptable key length (bits)
MAX_KEY_LENGTH = 128        # Maximum key length to retain
ERROR_THRESHOLD = 0.10      # 10% error rate triggers eavesdropper alert
SAMPLE_FRACTION = 0.10      # Fraction of key bits to sample for error check

# ─── Key Management ────────────────────────────────────────────
KEY_ROTATION_THRESHOLD = 0.75   # Rotate at 75% usage
AUTO_ROTATION = True

# ─── UI ─────────────────────────────────────────────────────────
TERMINAL_MIN_WIDTH = 80
TERMINAL_MIN_HEIGHT = 24
ANIMATION_SPEED = 0.03      # seconds between animation frames
SHOW_ENCRYPTION_DETAILS = True  # verbose mode default

# ─── Statistics ─────────────────────────────────────────────────
ENABLE_STATISTICS = True
