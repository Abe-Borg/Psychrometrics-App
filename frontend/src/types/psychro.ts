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
  | "heated_water_humidification"
  | "direct_evaporative"
  | "indirect_evaporative"
  | "indirect_direct_evaporative"
  | "chemical_dehumidification"
  | "sensible_reheat";

export type SensibleMode = "target_tdb" | "delta_t" | "heat_and_airflow";
export type CoolingDehumMode = "forward" | "reverse";
export type HumidificationMode = "target_rh" | "target_w" | "effectiveness";
export type DehumidificationMode = "target_rh" | "target_w";

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

  // Evaporative cooling (direct, indirect, two-stage)
  iec_effectiveness?: number;
  dec_effectiveness?: number;
  secondary_air_pair?: [string, string];
  secondary_air_values?: [number, number];

  // Chemical dehumidification
  dehum_mode?: DehumidificationMode;
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

// --- Coil analysis types ---

export type CoilMode = "forward" | "reverse";

export interface CoilInput {
  mode: CoilMode;
  unit_system: UnitSystem;
  pressure: number;
  entering_pair: [string, string];
  entering_values: [number, number];
  adp_Tdb?: number;
  bypass_factor?: number;
  leaving_pair?: [string, string];
  leaving_values?: [number, number];
  airflow?: number;
  water_entering_temp?: number;
  water_leaving_temp?: number;
}

export interface CoilOutput {
  unit_system: UnitSystem;
  pressure: number;
  mode: CoilMode;
  entering: StatePointOutput;
  leaving: StatePointOutput;
  adp: StatePointOutput;
  bypass_factor: number;
  contact_factor: number;
  Qs: number;
  Ql: number;
  Qt: number;
  SHR: number;
  load_unit: string;
  gpm: number | null;
  path_points: PathPoint[];
  warnings: string[];
}

// --- SHR types ---

export interface SHRLineInput {
  unit_system: UnitSystem;
  pressure: number;
  room_pair: [string, string];
  room_values: [number, number];
  shr: number;
}

export interface SHRLineOutput {
  room_point: StatePointOutput;
  shr: number;
  slope_dW_dTdb: number;
  line_points: PathPoint[];
  adp: StatePointOutput;
  adp_Tdb: number;
  warnings: string[];
}

export interface GSHRInput {
  unit_system: UnitSystem;
  pressure: number;
  room_pair: [string, string];
  room_values: [number, number];
  oa_pair: [string, string];
  oa_values: [number, number];
  room_sensible_load: number;
  room_total_load: number;
  oa_fraction: number;
  total_airflow: number;
  bypass_factor?: number;
}

export interface GSHROutput {
  room_point: StatePointOutput;
  oa_point: StatePointOutput;
  mixed_point: StatePointOutput;
  room_shr: number;
  gshr: number;
  eshr: number | null;
  room_shr_line: PathPoint[];
  gshr_line: PathPoint[];
  eshr_line: PathPoint[] | null;
  room_shr_adp: StatePointOutput;
  gshr_adp: StatePointOutput;
  eshr_adp: StatePointOutput | null;
  warnings: string[];
}

// --- Airflow calc types ---

export type CalcMode = "solve_q" | "solve_airflow" | "solve_delta";
export type LoadType = "sensible" | "latent" | "total";

export interface AirflowCalcInput {
  calc_mode: CalcMode;
  load_type: LoadType;
  unit_system: UnitSystem;
  pressure: number;
  Q?: number;
  airflow?: number;
  delta?: number;
  ref_Tdb?: number;
  ref_W?: number;
}

export interface AirflowCalcOutput {
  calc_mode: CalcMode;
  load_type: LoadType;
  unit_system: UnitSystem;
  Q: number;
  airflow: number;
  delta: number;
  C_factor: number;
  air_density: number;
  formula: string;
}

export interface CondensationCheckInput {
  surface_temp: number;
  state_pair: [string, string];
  state_values: [number, number];
  unit_system: UnitSystem;
  pressure: number;
}

export interface CondensationCheckOutput {
  is_condensing: boolean;
  surface_temp: number;
  dew_point: number;
  margin: number;
  unit_system: UnitSystem;
}

// --- Design Day types ---

export interface DesignDaySearchResult {
  name: string;
  state: string;
  country: string;
  climate_zone: string;
  elevation_ft: number;
}

export interface DesignDayResolvedPoint {
  condition_label: string;
  category: string;
  Tdb: number;
  Twb: number;
  Tdp: number;
  RH: number;
  W: number;
  W_display: number;
  h: number;
  v: number;
  unit_system: string;
}

export interface DesignDayResolveInput {
  location_name: string;
  location_state: string;
  condition_labels: string[];
  unit_system: UnitSystem;
  pressure?: number;
}

export interface DesignDayResolveOutput {
  location: DesignDaySearchResult;
  points: DesignDayResolvedPoint[];
  pressure_used: number;
  unit_system: string;
}

// --- TMY types ---

export interface TMYScatterPoint {
  Tdb: number;
  W_display: number;
  hour: number;
  month: number;
}

export interface TMYProcessOutput {
  unit_system: UnitSystem;
  scatter_points: TMYScatterPoint[];
  bin_Tdb_edges: number[];
  bin_W_edges: number[];
  bin_matrix: number[][];
  location_name: string | null;
  total_hours: number;
}

// --- AHU Wizard types ---

export type AHUType = "mixed_air" | "full_oa" | "economizer";

export interface AHUWizardInput {
  ahu_type: AHUType;
  unit_system: UnitSystem;
  pressure: number;
  oa_Tdb: number;
  oa_coincident: number;
  oa_input_type: string;
  ra_Tdb?: number;
  ra_RH?: number;
  oa_fraction?: number;
  oa_cfm?: number;
  ra_cfm?: number;
  supply_Tdb: number;
  supply_RH?: number;
  room_sensible_load?: number;
  room_total_load?: number;
  total_airflow?: number;
}

export interface AHUWizardOutput {
  ahu_type: AHUType;
  unit_system: UnitSystem;
  oa_point: StatePointOutput;
  ra_point: StatePointOutput | null;
  mixed_point: StatePointOutput | null;
  coil_leaving: StatePointOutput;
  supply_point: StatePointOutput;
  processes: ProcessOutput[];
  cooling_Qs: number;
  cooling_Ql: number;
  cooling_Qt: number;
  reheat_Q: number | null;
  shr: number;
  supply_cfm: number | null;
  adp_Tdb: number | null;
  bypass_factor: number | null;
  pressure: number;
  oa_fraction_used: number;
  needs_reheat: boolean;
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
