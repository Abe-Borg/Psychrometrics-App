/**
 * Client-side psychrometric property calculator for real-time hover tooltips.
 *
 * Uses the JS port of psychrolib so we don't need an API round-trip
 * on every mouse move. This is ONLY used for hover — all "real"
 * calculations (state points, processes) go through the backend.
 */
import * as psychrolib from "psychrolib";
import type { UnitSystem } from "../types/psychro";

export interface HoverProperties {
  Tdb: number;
  W_display: number;
  RH: number;
  Twb: number;
  Tdp: number;
  h: number;
  v: number;
}

const GRAINS_PER_LB = 7000;

/**
 * Given a cursor position (Tdb on x-axis, W_display on y-axis),
 * compute all psychrometric properties at that point.
 *
 * Returns null if the point is outside valid bounds (e.g., above saturation).
 */
export function calcPropertiesAtCursor(
  Tdb: number,
  W_display: number,
  pressure: number,
  unitSystem: UnitSystem
): HoverProperties | null {
  try {
    if (unitSystem === "IP") {
      psychrolib.SetUnitSystem(psychrolib.IP);
    } else {
      psychrolib.SetUnitSystem(psychrolib.SI);
    }

    // Convert display W back to lb/lb or kg/kg
    const W =
      unitSystem === "IP" ? W_display / GRAINS_PER_LB : W_display / 1000;

    if (W < 0) return null;

    // Check if above saturation
    const W_sat = psychrolib.GetSatHumRatio(Tdb, pressure);
    if (W > W_sat * 1.01) return null; // small tolerance

    const RH = psychrolib.GetRelHumFromHumRatio(Tdb, W, pressure);
    if (RH < 0 || RH > 1.01) return null;

    const Twb = psychrolib.GetTWetBulbFromHumRatio(Tdb, W, pressure);
    const Tdp = psychrolib.GetTDewPointFromHumRatio(Tdb, W, pressure);
    const h = psychrolib.GetMoistAirEnthalpy(Tdb, W);
    const v = psychrolib.GetMoistAirVolume(Tdb, W, pressure);

    return {
      Tdb,
      W_display,
      RH: RH * 100,
      Twb,
      Tdp,
      h,
      v,
    };
  } catch {
    return null;
  }
}
