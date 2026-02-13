"""
BB84 Quantum Chat - Photon Model
Represents a quantum photon used in the BB84 key distribution protocol.
"""

import time
from config.constants import ANGLES, ANGLE_SYMBOLS, BASIS_SYMBOLS


class Photon:
    """Represents a quantum photon with polarization encoding."""

    __slots__ = ('bit', 'basis', 'angle', 'timestamp')

    def __init__(self, bit: int, basis: int, angle: int = None):
        self.bit = bit          # 0 or 1
        self.basis = basis      # RECTILINEAR (0) or DIAGONAL (1)
        self.angle = angle if angle is not None else ANGLES[(bit, basis)]
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            'bit': self.bit,
            'basis': self.basis,
            'angle': self.angle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Photon':
        return cls(bit=data['bit'], basis=data['basis'], angle=data['angle'])

    @property
    def basis_symbol(self) -> str:
        return BASIS_SYMBOLS.get(self.basis, '?')

    @property
    def angle_symbol(self) -> str:
        return ANGLE_SYMBOLS.get(self.angle, '?')

    def __repr__(self) -> str:
        return f"Photon(bit={self.bit}, basis={self.basis_symbol}, angle={self.angle}°{self.angle_symbol})"
