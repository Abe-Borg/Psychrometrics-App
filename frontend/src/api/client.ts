import type { ChartData, StatePointInput, StatePointOutput, ProcessInput, ProcessOutput, CoilInput, CoilOutput, SHRLineInput, SHRLineOutput, GSHRInput, GSHROutput, AirflowCalcInput, AirflowCalcOutput, CondensationCheckInput, CondensationCheckOutput, UnitSystem } from "../types/psychro";

const BASE_URL = "/api/v1";

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error (${res.status}): ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function getChartData(
  unitSystem: UnitSystem = "IP",
  pressure?: number
): Promise<ChartData> {
  const params = new URLSearchParams({ unit_system: unitSystem });
  if (pressure !== undefined) {
    params.set("pressure", pressure.toString());
  }
  return fetchJSON<ChartData>(`${BASE_URL}/chart-data?${params}`);
}

export async function resolveStatePoint(
  input: StatePointInput
): Promise<StatePointOutput> {
  return fetchJSON<StatePointOutput>(`${BASE_URL}/state-point`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function calculateProcess(
  input: ProcessInput
): Promise<ProcessOutput> {
  return fetchJSON<ProcessOutput>(`${BASE_URL}/process`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function analyzeCoil(
  input: CoilInput
): Promise<CoilOutput> {
  return fetchJSON<CoilOutput>(`${BASE_URL}/coil`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function calculateSHRLine(
  input: SHRLineInput
): Promise<SHRLineOutput> {
  return fetchJSON<SHRLineOutput>(`${BASE_URL}/shr/line`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function calculateGSHR(
  input: GSHRInput
): Promise<GSHROutput> {
  return fetchJSON<GSHROutput>(`${BASE_URL}/shr/gshr`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function calculateAirflow(
  input: AirflowCalcInput
): Promise<AirflowCalcOutput> {
  return fetchJSON<AirflowCalcOutput>(`${BASE_URL}/airflow-calc`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function checkCondensation(
  input: CondensationCheckInput
): Promise<CondensationCheckOutput> {
  return fetchJSON<CondensationCheckOutput>(`${BASE_URL}/condensation-check`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getPressureFromAltitude(
  altitude: number,
  unitSystem: UnitSystem = "IP"
): Promise<{ altitude: number; pressure: number; unit_system: string }> {
  const params = new URLSearchParams({
    altitude: altitude.toString(),
    unit_system: unitSystem,
  });
  return fetchJSON(`${BASE_URL}/pressure-from-altitude?${params}`);
}
