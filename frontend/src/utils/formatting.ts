import type { UnitSystem } from "../types/psychro";

/** Property display labels with units */
export function getPropertyLabel(prop: string, unitSystem: UnitSystem): string {
  const labels: Record<string, Record<UnitSystem, string>> = {
    Tdb: { IP: "Tdb (°F)", SI: "Tdb (°C)" },
    Twb: { IP: "Twb (°F)", SI: "Twb (°C)" },
    Tdp: { IP: "Tdp (°F)", SI: "Tdp (°C)" },
    RH: { IP: "RH (%)", SI: "RH (%)" },
    W_display: { IP: "W (gr/lb)", SI: "W (g/kg)" },
    h: { IP: "h (BTU/lb)", SI: "h (kJ/kg)" },
    v: { IP: "v (ft³/lb)", SI: "v (m³/kg)" },
  };
  return labels[prop]?.[unitSystem] ?? prop;
}

/** Round to sensible precision for display */
export function fmt(value: number, decimals: number = 1): string {
  return value.toFixed(decimals);
}
