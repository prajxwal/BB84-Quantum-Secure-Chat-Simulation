"""
Tests for BB84 Protocol
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.bb84.photon import Photon
from src.bb84.protocol import (
    generate_random_bits, generate_random_bases, encode_photon,
    measure_photon, encode_photons, measure_photons,
    find_matching_positions, extract_key_bits, check_errors,
    remove_sample_bits, bb84_simulate,
)
from src.bb84.eavesdropper import Eve
from config.constants import RECTILINEAR, DIAGONAL


def test_generate_random_bits():
    """Bits should be 0 or 1."""
    bits = generate_random_bits(100)
    assert len(bits) == 100
    assert all(b in (0, 1) for b in bits)
    # Should have both 0s and 1s (probabilistic but extremely likely)
    assert sum(bits) > 0
    assert sum(bits) < 100


def test_generate_random_bases():
    """Bases should be RECTILINEAR(0) or DIAGONAL(1)."""
    bases = generate_random_bases(100)
    assert len(bases) == 100
    assert all(b in (RECTILINEAR, DIAGONAL) for b in bases)


def test_photon_encoding_rectilinear():
    """Test encoding bits in rectilinear basis."""
    p0 = encode_photon(0, RECTILINEAR)
    assert p0.bit == 0
    assert p0.basis == RECTILINEAR
    assert p0.angle == 0

    p1 = encode_photon(1, RECTILINEAR)
    assert p1.bit == 1
    assert p1.basis == RECTILINEAR
    assert p1.angle == 90


def test_photon_encoding_diagonal():
    """Test encoding bits in diagonal basis."""
    p0 = encode_photon(0, DIAGONAL)
    assert p0.bit == 0
    assert p0.basis == DIAGONAL
    assert p0.angle == 45

    p1 = encode_photon(1, DIAGONAL)
    assert p1.bit == 1
    assert p1.basis == DIAGONAL
    assert p1.angle == 135


def test_measure_photon_matching_basis():
    """Matching basis should always return the correct bit."""
    for bit in (0, 1):
        for basis in (RECTILINEAR, DIAGONAL):
            photon = encode_photon(bit, basis)
            result = measure_photon(photon, basis)
            assert result == bit, f"Expected {bit} for matching basis, got {result}"


def test_measure_photon_mismatching_basis():
    """Mismatching basis should give ~50/50 distribution."""
    photon = encode_photon(1, RECTILINEAR)
    results = [measure_photon(photon, DIAGONAL) for _ in range(200)]
    ones = sum(results)
    # Should be roughly 50% (with generous margin for randomness)
    assert 30 < ones < 170, f"Expected ~100 ones, got {ones}"


def test_find_matching_positions():
    """Should find positions where bases match."""
    alice_bases = [0, 1, 0, 1, 1]
    bob_bases = [0, 0, 0, 1, 1]
    matches = find_matching_positions(alice_bases, bob_bases)
    assert matches == [0, 2, 3, 4]


def test_extract_key_bits():
    """Should extract bits at specified positions."""
    bits = [1, 0, 1, 1, 0, 0, 1]
    positions = [0, 2, 4, 6]
    extracted = extract_key_bits(bits, positions)
    assert extracted == [1, 1, 0, 1]


def test_bb84_simulate_no_eve():
    """Full simulation without eavesdropper should produce matching keys."""
    result = bb84_simulate(num_photons=256, eve_intercept=False)
    assert not result['eavesdropper_detected']
    assert result['alice_final_key'] == result['bob_final_key']
    assert result['final_key_length'] > 0
    assert result['error_rate'] == 0.0


def test_bb84_simulate_with_eve():
    """Simulation with Eve should introduce errors."""
    eve = Eve()
    # Run multiple times to increase confidence
    detected_count = 0
    for _ in range(10):
        result = bb84_simulate(num_photons=256, eve_intercept=True, eve_instance=eve)
        if result['eavesdropper_detected']:
            detected_count += 1

    # Eve should be detected in most runs (statistically)
    assert detected_count >= 5, f"Eve detected only {detected_count}/10 times"


def test_photon_serialization():
    """Photon should serialize and deserialize correctly."""
    p = Photon(bit=1, basis=DIAGONAL, angle=135)
    d = p.to_dict()
    p2 = Photon.from_dict(d)
    assert p2.bit == 1
    assert p2.basis == DIAGONAL
    assert p2.angle == 135


def test_remove_sample_bits():
    """Should remove sampled positions from key."""
    key = [1, 0, 1, 1, 0, 0, 1]
    sample = [1, 3, 5]
    result = remove_sample_bits(key, sample)
    assert result == [1, 1, 0, 1]


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
