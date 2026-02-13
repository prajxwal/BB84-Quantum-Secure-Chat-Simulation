"""
BB84 Quantum Chat - BB84 Protocol Engine
Implements the full BB84 quantum key distribution simulation.
"""

import secrets
import random
from typing import List, Tuple, Optional

from config.constants import RECTILINEAR, DIAGONAL, ANGLES
from config.settings import NUM_PHOTONS, ERROR_THRESHOLD, SAMPLE_FRACTION, MIN_KEY_LENGTH
from src.bb84.photon import Photon


class EavesdropperDetectedError(Exception):
    """Raised when the BB84 error rate exceeds the security threshold."""
    def __init__(self, error_rate: float, threshold: float = ERROR_THRESHOLD):
        self.error_rate = error_rate
        self.threshold = threshold
        super().__init__(
            f"Eavesdropper detected! Error rate {error_rate:.1%} exceeds threshold {threshold:.1%}"
        )


class KeyTooShortError(Exception):
    """Raised when the generated key is shorter than the minimum length."""
    pass


# ─── Core Primitives ───────────────────────────────────────────


def generate_random_bits(n: int) -> List[int]:
    """Generate n cryptographically random bits using secrets module."""
    return [secrets.randbelow(2) for _ in range(n)]


def generate_random_bases(n: int) -> List[int]:
    """Generate n random measurement bases (RECTILINEAR or DIAGONAL)."""
    return [secrets.randbelow(2) for _ in range(n)]


def encode_photon(bit: int, basis: int) -> Photon:
    """Encode a bit as a polarized photon."""
    angle = ANGLES[(bit, basis)]
    return Photon(bit=bit, basis=basis, angle=angle)


def encode_photons(bits: List[int], bases: List[int]) -> List[Photon]:
    """Encode a list of bits with corresponding bases into photons."""
    return [encode_photon(b, ba) for b, ba in zip(bits, bases)]


def measure_photon(photon: Photon, measurement_basis: int) -> int:
    """
    Measure a photon with the given basis.
    If basis matches: correct bit recovered.
    If basis mismatches: random bit (50/50).
    """
    if photon.basis == measurement_basis:
        return photon.bit
    else:
        return random.randint(0, 1)


def measure_photons(photons: List[Photon], bases: List[int]) -> List[int]:
    """Measure a list of photons with corresponding bases."""
    return [measure_photon(p, b) for p, b in zip(photons, bases)]


# ─── Reconciliation ────────────────────────────────────────────


def find_matching_positions(alice_bases: List[int], bob_bases: List[int]) -> List[int]:
    """Find positions where Alice and Bob used the same basis."""
    return [i for i in range(len(alice_bases)) if alice_bases[i] == bob_bases[i]]


def extract_key_bits(bits: List[int], positions: List[int]) -> List[int]:
    """Extract bits at specified positions."""
    return [bits[i] for i in positions]


def check_errors(
    alice_key: List[int],
    bob_key: List[int],
    sample_fraction: float = SAMPLE_FRACTION,
) -> Tuple[float, List[int], List[int], List[int]]:
    """
    Sample a fraction of key bits and compare them to detect eavesdropping.

    Returns:
        - error_rate: fraction of mismatched sample bits
        - sample_positions: indices sampled (to remove from final key)
        - alice_sample: Alice's sample bits
        - bob_sample: Bob's sample bits
    """
    n = len(alice_key)
    sample_size = max(1, int(n * sample_fraction))
    sample_positions = sorted(random.sample(range(n), min(sample_size, n)))

    alice_sample = [alice_key[i] for i in sample_positions]
    bob_sample = [bob_key[i] for i in sample_positions]

    errors = sum(a != b for a, b in zip(alice_sample, bob_sample))
    error_rate = errors / len(sample_positions) if sample_positions else 0.0

    return error_rate, sample_positions, alice_sample, bob_sample


def remove_sample_bits(key: List[int], sample_positions: List[int]) -> List[int]:
    """Remove sampled bits from the key (privacy amplification step)."""
    sample_set = set(sample_positions)
    return [bit for i, bit in enumerate(key) if i not in sample_set]


# ─── Full Protocol (Local Simulation) ─────────────────────────


def bb84_simulate(
    num_photons: int = NUM_PHOTONS,
    eve_intercept: bool = False,
    eve_instance=None,
) -> dict:
    """
    Simulate the full BB84 protocol locally.
    Returns a dict with all intermediate and final data for visualization.

    Phases:
      1. Alice generates random bits
      2. Alice selects random bases
      3. Alice encodes photons
      4. (Optional) Eve intercepts
      5. Bob measures with random bases
      6. Basis reconciliation
      7. Error checking & key extraction
    """
    result = {}

    # Phase 1: Alice's random bits
    alice_bits = generate_random_bits(num_photons)
    result['alice_bits'] = alice_bits

    # Phase 2: Alice's random bases
    alice_bases = generate_random_bases(num_photons)
    result['alice_bases'] = alice_bases

    # Phase 3: Encode photons
    photons = encode_photons(alice_bits, alice_bases)
    result['photons'] = photons

    # Phase 4: Eve interception (optional)
    eve_bits = None
    eve_bases = None
    if eve_intercept and eve_instance:
        photons, eve_bits, eve_bases = eve_instance.intercept(photons)
    result['eve_active'] = eve_intercept
    result['eve_bits'] = eve_bits
    result['eve_bases'] = eve_bases
    result['transmitted_photons'] = photons

    # Phase 5: Bob measures with random bases
    bob_bases = generate_random_bases(num_photons)
    bob_bits = measure_photons(photons, bob_bases)
    result['bob_bases'] = bob_bases
    result['bob_bits'] = bob_bits

    # Phase 6: Basis reconciliation
    matching_positions = find_matching_positions(alice_bases, bob_bases)
    result['matching_positions'] = matching_positions
    result['match_rate'] = len(matching_positions) / num_photons

    alice_raw_key = extract_key_bits(alice_bits, matching_positions)
    bob_raw_key = extract_key_bits(bob_bits, matching_positions)
    result['alice_raw_key'] = alice_raw_key
    result['bob_raw_key'] = bob_raw_key

    # Phase 7: Error checking
    error_rate, sample_positions, alice_sample, bob_sample = check_errors(
        alice_raw_key, bob_raw_key
    )
    result['error_rate'] = error_rate
    result['sample_positions'] = sample_positions
    result['alice_sample'] = alice_sample
    result['bob_sample'] = bob_sample
    result['eavesdropper_detected'] = error_rate > ERROR_THRESHOLD

    # Final key (remove sampled bits)
    alice_final_key = remove_sample_bits(alice_raw_key, sample_positions)
    bob_final_key = remove_sample_bits(bob_raw_key, sample_positions)
    result['alice_final_key'] = alice_final_key
    result['bob_final_key'] = bob_final_key
    result['final_key_length'] = len(alice_final_key)
    result['key_too_short'] = len(alice_final_key) < MIN_KEY_LENGTH

    return result
