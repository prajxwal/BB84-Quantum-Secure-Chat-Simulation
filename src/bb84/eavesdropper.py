"""
BB84 Quantum Chat - Eavesdropper (Eve) Simulation
Simulates a man-in-the-middle attack on the quantum channel.
"""

import random
from typing import List, Tuple

from src.bb84.photon import Photon
from src.bb84.protocol import generate_random_bases, measure_photon, encode_photon


class Eve:
    """
    Simulates an eavesdropper intercepting BB84 photons.

    Eve measures each photon with a randomly chosen basis,
    then re-encodes a new photon based on her measurement result.
    When Eve's basis doesn't match Alice's, she disturbs the quantum
    state, introducing detectable errors.
    """

    def __init__(self):
        self.intercepted_count = 0
        self.last_bases = []
        self.last_bits = []

    def intercept(self, photons: List[Photon]) -> Tuple[List[Photon], List[int], List[int]]:
        """
        Intercept and re-encode photons.

        Returns:
            - modified_photons: photons as Eve forwards them to Bob
            - eve_bits: bits Eve measured
            - eve_bases: bases Eve used
        """
        n = len(photons)
        eve_bases = generate_random_bases(n)
        eve_bits = []
        modified_photons = []

        for photon, eve_basis in zip(photons, eve_bases):
            # Eve measures with her randomly chosen basis
            measured_bit = measure_photon(photon, eve_basis)
            eve_bits.append(measured_bit)

            # Eve re-encodes a new photon with what she measured
            new_photon = encode_photon(measured_bit, eve_basis)
            modified_photons.append(new_photon)

        self.intercepted_count += n
        self.last_bases = eve_bases
        self.last_bits = eve_bits

        return modified_photons, eve_bits, eve_bases
