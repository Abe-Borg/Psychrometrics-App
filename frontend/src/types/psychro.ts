export type UnitSystem = "IP" | "SI";

export interface StatePointInput {
  input_pair: [string, string];
  values: [number, number];
  pressure: number;
  unit_system: UnitSystem;
  label: string;
}

export interface StatePointOutput {
  label: string;
  unit_system: UnitSystem;
  pressure: number;
  input_pair: [string, string];
  input_values: [number, number];
  Tdb: number;
  Twb: number;
  Tdp: number;
  RH: number;
  W: number;
  W_display: number;
  h: number;
  v: number;
  Pv: number;
  Ps: number;
  mu: number;
}

export interface ChartPoint {
  Tdb: number;
  W: number;
  W_display: number;
}

export interface ChartRanges {
  Tdb_min: number;
  Tdb_max: number;
  W_min: number;
  W_max: number;
}

export interface ChartData {
  unit_system: string;
  pressure: number;
  ranges: ChartRanges;
  saturation_curve: ChartPoint[];
  rh_lines: Record<string, ChartPoint[]>;
  twb_lines: Record<string, ChartPoint[]>;
  enthalpy_lines: Record<string, ChartPoint[]>;
  volume_lines: Record<string, ChartPoint[]>;
}
