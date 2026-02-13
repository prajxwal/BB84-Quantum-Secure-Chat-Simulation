"""
BB84 Quantum Chat - Protocol Constants
"""

# ─── Basis Types ────────────────────────────────────────────────
RECTILINEAR = 0   # + basis (0° / 90°)
DIAGONAL = 1      # × basis (45° / 135°)

BASIS_SYMBOLS = {
    RECTILINEAR: '+',
    DIAGONAL: '×',
}

# ─── Polarization Angles ───────────────────────────────────────
ANGLES = {
    (0, RECTILINEAR): 0,     # bit=0, rectilinear → 0°
    (1, RECTILINEAR): 90,    # bit=1, rectilinear → 90°
    (0, DIAGONAL): 45,       # bit=0, diagonal → 45°
    (1, DIAGONAL): 135,      # bit=1, diagonal → 135°
}

ANGLE_SYMBOLS = {
    0:   '↔',    # horizontal
    90:  '↕',    # vertical
    45:  '↗',    # diagonal right
    135: '↖',    # diagonal left
}

# ─── Network Message Types ─────────────────────────────────────
MSG_CHAT          = 0x01
MSG_BB84_INIT     = 0x10
MSG_BB84_PHOTONS  = 0x11
MSG_BB84_BASES    = 0x12
MSG_BB84_MATCHES  = 0x13
MSG_BB84_SAMPLE   = 0x14
MSG_BB84_VERIFY   = 0x15
MSG_BB84_COMPLETE = 0x16
MSG_BB84_ABORT    = 0x17
MSG_KEY_ROTATE    = 0x20
MSG_COMMAND       = 0x30
MSG_STATUS        = 0x40
MSG_EVE_TOGGLE    = 0x50
MSG_DISCONNECT    = 0xFE
MSG_ERROR         = 0xFF
