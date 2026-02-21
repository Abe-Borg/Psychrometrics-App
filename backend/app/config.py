"""
PsychroApp configuration and constants.
"""

from enum import Enum


class UnitSystem(str, Enum):
    IP = "IP"  # Inch-Pound (°F, BTU, grains, ft³, psi)
    SI = "SI"  # Metric (°C, kJ, g/kg, m³, Pa)


# Supported input pair combinations for state point resolution.
# Each pair must consist of two independent psychrometric properties.
SUPPORTED_INPUT_PAIRS: list[tuple[str, str]] = [
    ("Tdb", "RH"),
    ("Tdb", "Twb"),
    ("Tdb", "Tdp"),
    ("Tdb", "W"),
    ("Tdb", "h"),
    ("Twb", "RH"),
    ("Tdp", "RH"),
]

# Default atmospheric pressure at sea level
DEFAULT_PRESSURE_IP = 14.696  # psia
DEFAULT_PRESSURE_SI = 101325.0  # Pa

# Default altitude (sea level)
DEFAULT_ALTITUDE_IP = 0.0  # feet
DEFAULT_ALTITUDE_SI = 0.0  # meters

# Grains per lb conversion
GRAINS_PER_LB = 7000.0

# Chart axis ranges
CHART_RANGES = {
    "IP": {
        "Tdb_min": 20.0,   # °F
        "Tdb_max": 120.0,  # °F
        "W_min": 0.0,      # grains/lb
        "W_max": 220.0,    # grains/lb
    },
    "SI": {
        "Tdb_min": -10.0,  # °C
        "Tdb_max": 55.0,   # °C
        "W_min": 0.0,      # g/kg (grams per kg dry air)
        "W_max": 30.0,     # g/kg
    },
}

# Property labels and units for display
PROPERTY_UNITS = {
    "IP": {
        "Tdb": "°F",
        "Twb": "°F",
        "Tdp": "°F",
        "RH": "%",
        "W": "lb_w/lb_da",
        "W_grains": "gr/lb",
        "h": "BTU/lb_da",
        "v": "ft³/lb_da",
        "Pv": "psi",
        "Ps": "psi",
        "mu": "",
    },
    "SI": {
        "Tdb": "°C",
        "Twb": "°C",
        "Tdp": "°C",
        "RH": "%",
        "W": "kg_w/kg_da",
        "W_gpkg": "g/kg",
        "h": "kJ/kg_da",
        "v": "m³/kg_da",
        "Pv": "Pa",
        "Ps": "Pa",
        "mu": "",
    },
}
