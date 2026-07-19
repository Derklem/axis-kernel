import pytest
from laboratory.crypto import canonical_hash, validate_canonical_numbers

def test_canonical_number_boundaries():
    # Valid integers
    validate_canonical_numbers({"n": 9_007_199_254_740_991})
    validate_canonical_numbers({"n": -9_007_199_254_740_991})
    validate_canonical_numbers({"n": 0})
    validate_canonical_numbers({"n": True})
    validate_canonical_numbers({"n": False})
    
    # Check canonical hashing itself accepts these
    assert isinstance(canonical_hash({"n": 9_007_199_254_740_991}), str)
    assert isinstance(canonical_hash({"n": -9_007_199_254_740_991}), str)

    # Invalid integers (oversized)
    with pytest.raises(ValueError, match="Integer outside safe interoperable bounds"):
        validate_canonical_numbers({"n": 9_007_199_254_740_992})
        
    with pytest.raises(ValueError, match="Integer outside safe interoperable bounds"):
        validate_canonical_numbers({"n": -9_007_199_254_740_992})

    # Floating point
    with pytest.raises(ValueError, match="Floating-point numbers are prohibited"):
        validate_canonical_numbers({"n": 3.14})
        
    # Check canonical_hash rejects oversized
    with pytest.raises(ValueError, match="Integer outside safe interoperable bounds"):
        canonical_hash({"n": 9_007_199_254_740_992})
