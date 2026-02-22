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

// --- Process types ---

export type ProcessType =
  | "sensible_heating"
  | "sensible_cooling"
  | "cooling_dehumidification"
  | "adiabatic_mixing"
  | "steam_humidification"
  | "adiabatic_humidification"
  | "heated_water_humidification";

export type SensibleMode = "target_tdb" | "delta_t" | "heat_and_airflow";
export type CoolingDehumMode = "forward" | "reverse";
export type HumidificationMode = "target_rh" | "target_w" | "effectiveness";

export interface PathPoint {
  Tdb: number;
  W: number;
  W_display: number;
}

export interface ProcessInput {
  process_type: ProcessType;
  unit_system: UnitSystem;
  pressure: number;
  start_point_pair: [string, string];
  start_point_values: [number, number];

  // Sensible heating/cooling
  sensible_mode?: SensibleMode;
  target_Tdb?: number;
  delta_T?: number;
  Q_sensible?: number;
  airflow_cfm?: number;

  // Cooling & dehumidification
  cooling_dehum_mode?: CoolingDehumMode;
  adp_Tdb?: number;
  bypass_factor?: number;
  leaving_Tdb?: number;
  leaving_RH?: number;

  // Adiabatic mixing
  stream2_point_pair?: [string, string];
  stream2_point_values?: [number, number];
  mixing_fraction?: number;

  // Humidification (steam, adiabatic, heated water)
  humidification_mode?: HumidificationMode;
  target_RH?: number;
  target_W?: number;
  effectiveness?: number;
  water_temperature?: number;
}

export interface ProcessOutput {
  process_type: ProcessType;
  unit_system: UnitSystem;
  pressure: number;
  start_point: StatePointOutput;
  end_point: StatePointOutput;
  path_points: PathPoint[];
  metadata: Record<string, unknown>;
  warnings: string[];
}

// --- Chart types ---

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
