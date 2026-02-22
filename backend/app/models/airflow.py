"""
Pydantic models for airflow and energy calculations.

Provides models for:
  - Airflow/load calculation: solve for Q, CFM, or delta given the other two
  - Condensation check: compare surface temperature against air dew point
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel

from app.config import UnitSystem, DEFAULT_PRESSURE_IP


class CalcMode(str, Enum):
    SOLVE_Q = "solve_q"              # Solve for heat load (Q)
    SOLVE_AIRFLOW = "solve_airflow"  # Solve for CFM (IP) or m³/s (SI)
    SOLVE_DELTA = "solve_delta"      # Solve for ΔT, ΔW, or Δh


class LoadType(str, Enum):
    SENSIBLE = "sensible"  # Qs = Cs × CFM × ΔT
    LATENT = "latent"      # Ql = Cl × CFM × ΔW
    TOTAL = "total"        # Qt = Ct × CFM × Δh


class AirflowCalcInput(BaseModel):
    """Input for airflow/energy calculation."""
    calc_mode: CalcMode
    load_type: LoadType
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Two of these three are provided; the third is solved
    Q: Optional[float] = None          # BTU/hr (IP) or W (SI)
    airflow: Optional[float] = None    # CFM (IP) or m³/s (SI)
    delta: Optional[float] = None      # ΔT, ΔW (lb/lb or kg/kg), or Δh (BTU/lb or kJ/kg)

    # Reference conditions for density/C-factor calculation
    ref_Tdb: Optional[float] = None    # Reference dry-bulb temperature
    ref_W: Optional[float] = None      # Reference humidity ratio (lb/lb or kg/kg)


class AirflowCalcOutput(BaseModel):
    """Result of airflow/energy calculation."""
    calc_mode: CalcMode
    load_type: LoadType
    unit_system: UnitSystem
    Q: float
    airflow: float
    delta: float
    C_factor: float         # Altitude-corrected C constant used
    air_density: float      # Air density (lb/ft³ or kg/m³) at reference conditions
    formula: str            # Human-readable formula string


class CondensationCheckInput(BaseModel):
    """Input for condensation risk check."""
    surface_temp: float                    # Surface temperature (°F or °C)
    state_pair: tuple[str, str]            # Input pair to resolve the air state
    state_values: tuple[float, float]      # Values for the input pair
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP


class CondensationCheckOutput(BaseModel):
    """Result of condensation risk check."""
    is_condensing: bool
    surface_temp: float
    dew_point: float
    margin: float           # surface_temp - dew_point (negative = condensing)
    unit_system: UnitSystem
