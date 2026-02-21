"""
Tests for the state point resolver.

Reference values are validated against ASHRAE Fundamentals handbook
psychrometric tables and cross-checked with psychrolib's own test suite.

All IP tests use standard atmospheric pressure: 14.696 psia.
"""

import pytest
from app.config import UnitSystem, DEFAULT_PRESSURE_IP, DEFAULT_PRESSURE_SI
from app.engine.state_resolver import resolve_state_point, get_pressure_from_altitude


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def approx(value: float, rel_tol: float = 0.01, abs_tol: float = 0.1):
    """
    Approximate comparison helper.
    Default tolerance: 1% relative or 0.1 absolute (whichever is larger).
    Psychrometric calcs can have small rounding differences between sources.
    """
    return pytest.approx(value, rel=rel_tol, abs=abs_tol)


# ---------------------------------------------------------------------------
# Test: Tdb + RH input pair (IP)
# ---------------------------------------------------------------------------

class TestTdbRhIP:
    """Standard conditions: 75°F, 50% RH at sea level."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(75.0, 50.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
            label="Room",
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(75.0)

    def test_relative_humidity(self):
        assert self.result.RH == approx(50.0)

    def test_wet_bulb(self):
        # Expected ~62.5-63°F at 75°F/50% RH
        assert 61.0 <= self.result.Twb <= 64.0

    def test_dew_point(self):
        # Expected ~55.0-55.5°F
        assert 54.0 <= self.result.Tdp <= 57.0

    def test_humidity_ratio_grains(self):
        # Expected ~65-66 grains/lb
        assert 63.0 <= self.result.W_display <= 68.0

    def test_enthalpy(self):
        # Expected ~28.1-28.3 BTU/lb
        assert 27.0 <= self.result.h <= 30.0

    def test_specific_volume(self):
        # Expected ~13.67-13.7 ft³/lb
        assert 13.5 <= self.result.v <= 13.9

    def test_label(self):
        assert self.result.label == "Room"

    def test_unit_system(self):
        assert self.result.unit_system == UnitSystem.IP


class TestTdbRhIP_Hot:
    """Hot outdoor conditions: 95°F, 40% RH (typical California summer)."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(95.0, 40.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(95.0)

    def test_relative_humidity(self):
        assert self.result.RH == approx(40.0)

    def test_wet_bulb(self):
        # Expected ~76-78°F
        assert 75.0 <= self.result.Twb <= 80.0

    def test_humidity_ratio_grains(self):
        # Expected ~98-100 grains/lb
        assert 95.0 <= self.result.W_display <= 105.0

    def test_enthalpy(self):
        # Expected ~38-40 BTU/lb
        assert 37.0 <= self.result.h <= 42.0


class TestTdbRhIP_Saturated:
    """Saturated air: 55°F, 100% RH (typical coil leaving condition)."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(55.0, 100.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_tdb_equals_twb_equals_tdp(self):
        # At saturation, all three temperatures converge
        assert self.result.Twb == approx(55.0, abs_tol=0.3)
        assert self.result.Tdp == approx(55.0, abs_tol=0.3)

    def test_degree_of_saturation(self):
        assert self.result.mu == approx(1.0, abs_tol=0.01)


# ---------------------------------------------------------------------------
# Test: Tdb + Twb input pair (IP)
# ---------------------------------------------------------------------------

class TestTdbTwbIP:
    """75°F db / 62.5°F wb — should match ~50% RH conditions."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "Twb"),
            values=(75.0, 62.5),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(75.0)

    def test_wet_bulb(self):
        assert self.result.Twb == approx(62.5)

    def test_rh_approximately_50(self):
        assert 47.0 <= self.result.RH <= 53.0


# ---------------------------------------------------------------------------
# Test: Tdb + Tdp input pair (IP)
# ---------------------------------------------------------------------------

class TestTdbTdpIP:
    """75°F db / 55°F dew point."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "Tdp"),
            values=(75.0, 55.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(75.0)

    def test_dew_point(self):
        assert self.result.Tdp == approx(55.0)

    def test_rh_reasonable(self):
        # Tdp of 55 at Tdb 75 should give ~48-52% RH
        assert 45.0 <= self.result.RH <= 55.0


# ---------------------------------------------------------------------------
# Test: Tdb + W input pair (IP)
# ---------------------------------------------------------------------------

class TestTdbWIP:
    """75°F db, W = 0.0093 lb/lb (~65 grains)."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(75.0, 0.0093),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(75.0)

    def test_humidity_ratio(self):
        assert self.result.W == approx(0.0093, abs_tol=0.0001)

    def test_grains(self):
        assert self.result.W_display == approx(65.1, abs_tol=1.0)

    def test_rh_reasonable(self):
        assert 45.0 <= self.result.RH <= 55.0


# ---------------------------------------------------------------------------
# Test: Tdb + h input pair (IP) — iterative solver
# ---------------------------------------------------------------------------

class TestTdbEnthalpyIP:
    """75°F db, h = 28.2 BTU/lb."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "h"),
            values=(75.0, 28.2),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(75.0)

    def test_enthalpy(self):
        assert self.result.h == approx(28.2, abs_tol=0.2)

    def test_rh_reasonable(self):
        assert 45.0 <= self.result.RH <= 55.0


# ---------------------------------------------------------------------------
# Test: Twb + RH input pair (IP) — iterative solver
# ---------------------------------------------------------------------------

class TestTwbRhIP:
    """Twb = 62.5°F, RH = 50% — should resolve to ~75°F db."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Twb", "RH"),
            values=(62.5, 50.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_wet_bulb(self):
        assert self.result.Twb == approx(62.5, abs_tol=0.5)

    def test_rh(self):
        assert self.result.RH == approx(50.0, abs_tol=1.0)

    def test_tdb_approximately_75(self):
        assert 73.0 <= self.result.Tdb <= 77.0


# ---------------------------------------------------------------------------
# Test: Tdp + RH input pair (IP) — iterative solver
# ---------------------------------------------------------------------------

class TestTdpRhIP:
    """Tdp = 55°F, RH = 50%."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdp", "RH"),
            values=(55.0, 50.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_dew_point(self):
        assert self.result.Tdp == approx(55.0, abs_tol=0.5)

    def test_rh(self):
        assert self.result.RH == approx(50.0, abs_tol=1.0)

    def test_tdb_reasonable(self):
        # Tdp 55 at 50% RH should give Tdb around 74-76°F
        assert 72.0 <= self.result.Tdb <= 78.0


# ---------------------------------------------------------------------------
# Test: Reverse input pair ordering
# ---------------------------------------------------------------------------

class TestReversePairOrdering:
    """Input pair can be given in either order, e.g. ('RH', 'Tdb') instead of ('Tdb', 'RH')."""

    def test_rh_tdb_reversed(self):
        result = resolve_state_point(
            input_pair=("RH", "Tdb"),
            values=(50.0, 75.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )
        assert result.Tdb == approx(75.0)
        assert result.RH == approx(50.0)


# ---------------------------------------------------------------------------
# Test: SI unit system
# ---------------------------------------------------------------------------

class TestSIUnits:
    """24°C, 50% RH at standard atmospheric pressure."""

    def setup_method(self):
        self.result = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(24.0, 50.0),
            pressure=DEFAULT_PRESSURE_SI,
            unit_system=UnitSystem.SI,
        )

    def test_dry_bulb(self):
        assert self.result.Tdb == approx(24.0)

    def test_rh(self):
        assert self.result.RH == approx(50.0)

    def test_humidity_ratio_grams_per_kg(self):
        # ~9.3 g/kg at 24°C/50%
        assert 8.5 <= self.result.W_display <= 10.0

    def test_unit_system(self):
        assert self.result.unit_system == UnitSystem.SI


# ---------------------------------------------------------------------------
# Test: Altitude / pressure conversion
# ---------------------------------------------------------------------------

class TestAltitudePressure:
    def test_sea_level_ip(self):
        p = get_pressure_from_altitude(0.0, UnitSystem.IP)
        assert p == approx(DEFAULT_PRESSURE_IP, abs_tol=0.01)

    def test_sea_level_si(self):
        p = get_pressure_from_altitude(0.0, UnitSystem.SI)
        assert p == approx(DEFAULT_PRESSURE_SI, abs_tol=50)

    def test_denver_altitude_ip(self):
        # Denver ~5280 ft, expected ~12.1-12.2 psia
        p = get_pressure_from_altitude(5280.0, UnitSystem.IP)
        assert 12.0 <= p <= 12.5

    def test_higher_altitude_lower_pressure(self):
        p_sea = get_pressure_from_altitude(0.0, UnitSystem.IP)
        p_high = get_pressure_from_altitude(5000.0, UnitSystem.IP)
        assert p_high < p_sea


# ---------------------------------------------------------------------------
# Test: Error handling
# ---------------------------------------------------------------------------

class TestErrors:
    def test_unsupported_pair(self):
        with pytest.raises(ValueError, match="Unsupported input pair"):
            resolve_state_point(
                input_pair=("h", "v"),
                values=(28.0, 13.5),
                pressure=DEFAULT_PRESSURE_IP,
                unit_system=UnitSystem.IP,
            )

    def test_enthalpy_out_of_range(self):
        with pytest.raises(ValueError, match="outside the achievable range"):
            resolve_state_point(
                input_pair=("Tdb", "h"),
                values=(75.0, 200.0),  # impossibly high enthalpy at 75°F
                pressure=DEFAULT_PRESSURE_IP,
                unit_system=UnitSystem.IP,
            )


# ---------------------------------------------------------------------------
# Test: Cross-consistency (resolve from different pairs, same conditions)
# ---------------------------------------------------------------------------

class TestCrossConsistency:
    """
    Resolve the same physical state from different input pairs.
    All results should produce the same properties (within tolerance).
    """

    def setup_method(self):
        # First, get a reference from Tdb+RH
        self.ref = resolve_state_point(
            input_pair=("Tdb", "RH"),
            values=(75.0, 50.0),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )

    def test_tdb_twb_matches(self):
        result = resolve_state_point(
            input_pair=("Tdb", "Twb"),
            values=(self.ref.Tdb, self.ref.Twb),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )
        assert result.RH == approx(self.ref.RH, abs_tol=0.5)
        assert result.W == approx(self.ref.W, abs_tol=0.0002)
        assert result.h == approx(self.ref.h, abs_tol=0.2)

    def test_tdb_tdp_matches(self):
        result = resolve_state_point(
            input_pair=("Tdb", "Tdp"),
            values=(self.ref.Tdb, self.ref.Tdp),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )
        assert result.RH == approx(self.ref.RH, abs_tol=0.5)
        assert result.W == approx(self.ref.W, abs_tol=0.0002)

    def test_tdb_w_matches(self):
        result = resolve_state_point(
            input_pair=("Tdb", "W"),
            values=(self.ref.Tdb, self.ref.W),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )
        assert result.RH == approx(self.ref.RH, abs_tol=0.5)
        assert result.Twb == approx(self.ref.Twb, abs_tol=0.3)

    def test_tdb_h_matches(self):
        result = resolve_state_point(
            input_pair=("Tdb", "h"),
            values=(self.ref.Tdb, self.ref.h),
            pressure=DEFAULT_PRESSURE_IP,
            unit_system=UnitSystem.IP,
        )
        assert result.RH == approx(self.ref.RH, abs_tol=1.0)
        assert result.W == approx(self.ref.W, abs_tol=0.0003)
