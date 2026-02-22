import type { ChartData, StatePointInput, StatePointOutput, ProcessInput, ProcessOutput, UnitSystem } from "../types/psychro";

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
