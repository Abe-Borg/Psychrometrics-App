import { useState } from "react";
import { useStore } from "../../store/useStore";
import { calculateAirflow, checkCondensation } from "../../api/client";
import { fmt } from "../../utils/formatting";
import type { CalcMode, LoadType } from "../../types/psychro";

const LOAD_TYPES: { value: LoadType; label: string }[] = [
  { value: "sensible", label: "Sensible (Qs)" },
  { value: "latent", label: "Latent (Ql)" },
  { value: "total", label: "Total (Qt)" },
];

const CALC_MODES: { value: CalcMode; label: string }[] = [
  { value: "solve_q", label: "Solve for Q" },
  { value: "solve_airflow", label: "Solve for Airflow" },
  { value: "solve_delta", label: "Solve for Delta" },
];

const INPUT_PAIRS: { value: [string, string]; label: string }[] = [
  { value: ["Tdb", "RH"], label: "Tdb + RH" },
  { value: ["Tdb", "Twb"], label: "Tdb + Twb" },
  { value: ["Tdb", "Tdp"], label: "Tdb + Tdp" },
  { value: ["Tdb", "W"], label: "Tdb + W (lb/lb)" },
  { value: ["Tdb", "h"], label: "Tdb + h" },
  { value: ["Twb", "RH"], label: "Twb + RH" },
  { value: ["Tdp", "RH"], label: "Tdp + RH" },
];

function getFieldLabels(
  pair: [string, string],
  unitSystem: string
): [string, string] {
  const isIP = unitSystem === "IP";
  const labels: Record<string, string> = {
    Tdb: isIP ? "Dry-Bulb (\u00b0F)" : "Dry-Bulb (\u00b0C)",
    Twb: isIP ? "Wet-Bulb (\u00b0F)" : "Wet-Bulb (\u00b0C)",
    Tdp: isIP ? "Dew Point (\u00b0F)" : "Dew Point (\u00b0C)",
    RH: "RH (%)",
    W: isIP ? "W (lb/lb)" : "W (kg/kg)",
    h: isIP ? "h (BTU/lb)" : "h (kJ/kg)",
  };
  return [labels[pair[0]] ?? pair[0], labels[pair[1]] ?? pair[1]];
}

function getFieldStep(prop: string): number {
  if (prop === "W") return 0.0001;
  if (prop === "h") return 0.1;
  return 1;
}

function getDeltaLabel(loadType: LoadType, isIP: boolean): string {
  if (loadType === "sensible") return isIP ? "\u0394T (\u00b0F)" : "\u0394T (\u00b0C)";
  if (loadType === "latent") return isIP ? "\u0394W (lb/lb)" : "\u0394W (kg/kg)";
  return isIP ? "\u0394h (BTU/lb)" : "\u0394h (kJ/kg)";
}

function getDeltaStep(loadType: LoadType): number {
  if (loadType === "latent") return 0.0001;
  if (loadType === "total") return 0.1;
  return 1;
}

function getQLabel(isIP: boolean): string {
  return isIP ? "Q (BTU/hr)" : "Q (W)";
}

function getAirflowLabel(isIP: boolean): string {
  return isIP ? "Airflow (CFM)" : "Airflow (m\u00b3/s)";
}

const selectClass =
  "w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm text-text-primary focus:outline-none focus:border-accent cursor-pointer";
const inputClass =
  "w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm text-text-primary focus:outline-none focus:border-accent";

export default function AirflowCalc() {
  const { unitSystem, pressure, processes, statePoints, airflowResult, setAirflowResult, condensationResult, setCondensationResult, addToast } = useStore();
  const isIP = unitSystem === "IP";

  // Airflow calc form
  const [loadType, setLoadType] = useState<LoadType>("sensible");
  const [calcMode, setCalcMode] = useState<CalcMode>("solve_q");
  const [qValue, setQValue] = useState("");
  const [airflowValue, setAirflowValue] = useState("");
  const [deltaValue, setDeltaValue] = useState("");
  const [refTdb, setRefTdb] = useState("");
  const [refW, setRefW] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Condensation check
  const [condExpanded, setCondExpanded] = useState(false);
  const [surfaceTemp, setSurfaceTemp] = useState("");
  const [condPairIndex, setCondPairIndex] = useState(0);
  const [condVal1, setCondVal1] = useState("");
  const [condVal2, setCondVal2] = useState("");
  const [condLoading, setCondLoading] = useState(false);
  const [condError, setCondError] = useState<string | null>(null);

  const condPair = INPUT_PAIRS[condPairIndex].value;
  const [condLabel1, condLabel2] = getFieldLabels(condPair, unitSystem);

  async function handleCalcSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const input: Parameters<typeof calculateAirflow>[0] = {
      calc_mode: calcMode,
      load_type: loadType,
      unit_system: unitSystem,
      pressure,
    };

    // Set the two known values based on calc_mode
    if (calcMode === "solve_q") {
      const af = parseFloat(airflowValue);
      const d = parseFloat(deltaValue);
      if (isNaN(af) || isNaN(d)) { setError("Enter valid airflow and delta values"); return; }
      input.airflow = af;
      input.delta = d;
    } else if (calcMode === "solve_airflow") {
      const q = parseFloat(qValue);
      const d = parseFloat(deltaValue);
      if (isNaN(q) || isNaN(d)) { setError("Enter valid Q and delta values"); return; }
      input.Q = q;
      input.delta = d;
    } else {
      const q = parseFloat(qValue);
      const af = parseFloat(airflowValue);
      if (isNaN(q) || isNaN(af)) { setError("Enter valid Q and airflow values"); return; }
      input.Q = q;
      input.airflow = af;
    }

    // Optional reference conditions
    const rt = parseFloat(refTdb);
    const rw = parseFloat(refW);
    if (!isNaN(rt)) input.ref_Tdb = rt;
    if (!isNaN(rw)) input.ref_W = rw;

    setLoading(true);
    try {
      const result = await calculateAirflow(input);
      setAirflowResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Calculation failed";
      setError(msg);
      addToast(msg, "error");
    } finally {
      setLoading(false);
    }
  }

  function handleAutoFillFromProcess(idx: number) {
    const proc = processes[idx];
    if (!proc) return;

    const start = proc.start_point;
    const end = proc.end_point;

    if (loadType === "sensible") {
      setDeltaValue(String(Math.abs(end.Tdb - start.Tdb).toFixed(4)));
    } else if (loadType === "latent") {
      setDeltaValue(String(Math.abs(end.W - start.W).toFixed(6)));
    } else {
      setDeltaValue(String(Math.abs(end.h - start.h).toFixed(4)));
    }

    // Auto-fill reference conditions from the start point
    setRefTdb(String(start.Tdb));
    setRefW(String(start.W));
  }

  async function handleCondCheck(e: React.FormEvent) {
    e.preventDefault();
    setCondError(null);

    const st = parseFloat(surfaceTemp);
    const v1 = parseFloat(condVal1);
    const v2 = parseFloat(condVal2);
    if (isNaN(st)) { setCondError("Enter a valid surface temperature"); return; }
    if (isNaN(v1) || isNaN(v2)) { setCondError("Enter valid air conditions"); return; }

    setCondLoading(true);
    try {
      const result = await checkCondensation({
        surface_temp: st,
        state_pair: condPair,
        state_values: [v1, v2],
        unit_system: unitSystem,
        pressure,
      });
      setCondensationResult(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Condensation check failed";
      setCondError(msg);
      addToast(msg, "error");
    } finally {
      setCondLoading(false);
    }
  }

  function handleAutoFillCondFromPoint(idx: number) {
    const sp = statePoints[idx];
    if (!sp) return;
    setCondPairIndex(0); // Tdb + RH
    setCondVal1(String(sp.Tdb));
    setCondVal2(String(sp.RH));
  }

  const tUnit = isIP ? "\u00b0F" : "\u00b0C";

  return (
    <div className="flex flex-col gap-4">
      {/* Airflow/Load Calculator */}
      <form onSubmit={handleCalcSubmit} className="flex flex-col gap-3">
        {/* Load type */}
        <div>
          <label className="block text-xs text-text-muted mb-1">Load Type</label>
          <select
            value={loadType}
            onChange={(e) => setLoadType(e.target.value as LoadType)}
            className={selectClass}
          >
            {LOAD_TYPES.map((lt) => (
              <option key={lt.value} value={lt.value}>{lt.label}</option>
            ))}
          </select>
        </div>

        {/* Solve for */}
        <div>
          <label className="block text-xs text-text-muted mb-1">Solve For</label>
          <select
            value={calcMode}
            onChange={(e) => setCalcMode(e.target.value as CalcMode)}
            className={selectClass}
          >
            {CALC_MODES.map((cm) => (
              <option key={cm.value} value={cm.value}>{cm.label}</option>
            ))}
          </select>
        </div>

        {/* Input fields — show the two known values */}
        <div className="grid grid-cols-2 gap-2">
          {calcMode !== "solve_q" && (
            <div className={calcMode === "solve_airflow" ? "col-span-2" : ""}>
              <label className="block text-xs text-text-muted mb-1">{getQLabel(isIP)}</label>
              <input
                type="number"
                value={qValue}
                onChange={(e) => setQValue(e.target.value)}
                step={1000}
                placeholder="\u2014"
                className={inputClass}
              />
            </div>
          )}
          {calcMode !== "solve_airflow" && (
            <div className={calcMode === "solve_q" ? "" : ""}>
              <label className="block text-xs text-text-muted mb-1">{getAirflowLabel(isIP)}</label>
              <input
                type="number"
                value={airflowValue}
                onChange={(e) => setAirflowValue(e.target.value)}
                step={isIP ? 100 : 0.1}
                placeholder="\u2014"
                className={inputClass}
              />
            </div>
          )}
          {calcMode !== "solve_delta" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">{getDeltaLabel(loadType, isIP)}</label>
              <input
                type="number"
                value={deltaValue}
                onChange={(e) => setDeltaValue(e.target.value)}
                step={getDeltaStep(loadType)}
                placeholder="\u2014"
                className={inputClass}
              />
            </div>
          )}
        </div>

        {/* Auto-fill from process */}
        {processes.length > 0 && (
          <div>
            <label className="block text-xs text-text-muted mb-1">Auto-fill delta from process</label>
            <select
              onChange={(e) => {
                const idx = parseInt(e.target.value);
                if (!isNaN(idx)) handleAutoFillFromProcess(idx);
              }}
              defaultValue=""
              className={selectClass}
            >
              <option value="" disabled>Select a process...</option>
              {processes.map((p, i) => (
                <option key={i} value={i}>
                  {p.process_type} ({fmt(p.start_point.Tdb, 1)} → {fmt(p.end_point.Tdb, 1)})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Reference conditions (optional) */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">Ref Tdb ({tUnit}) &mdash; opt.</label>
            <input
              type="number"
              value={refTdb}
              onChange={(e) => setRefTdb(e.target.value)}
              step={1}
              placeholder={isIP ? "70" : "21"}
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Ref W &mdash; opt.</label>
            <input
              type="number"
              value={refW}
              onChange={(e) => setRefW(e.target.value)}
              step={0.001}
              placeholder="0.01"
              className={inputClass}
            />
          </div>
        </div>

        {error && (
          <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">{error}</div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                     rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {loading ? "Calculating..." : "Calculate"}
        </button>
      </form>

      {/* Results */}
      {airflowResult && (
        <div className="bg-bg-tertiary border border-border rounded p-3 text-xs">
          <div className="font-semibold text-text-primary mb-2">Result</div>

          <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2">
            <span className="text-text-muted">{getQLabel(isIP)}</span>
            <span className="text-text-primary text-right">{Number(airflowResult.Q).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
            <span className="text-text-muted">{getAirflowLabel(isIP)}</span>
            <span className="text-text-primary text-right">{Number(airflowResult.airflow).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
            <span className="text-text-muted">{getDeltaLabel(airflowResult.load_type, isIP)}</span>
            <span className="text-text-primary text-right">{fmt(airflowResult.delta, 4)}</span>
          </div>

          <div className="border-t border-border pt-2 mt-2">
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <span className="text-text-muted">C factor</span>
              <span className="text-text-primary text-right">{fmt(airflowResult.C_factor, 4)}</span>
              <span className="text-text-muted">Air density</span>
              <span className="text-text-primary text-right">
                {fmt(airflowResult.air_density, 4)} {isIP ? "lb/ft\u00b3" : "kg/m\u00b3"}
              </span>
            </div>
          </div>

          <div className="border-t border-border pt-2 mt-2">
            <div className="text-text-secondary font-mono text-[11px] break-all">
              {airflowResult.formula}
            </div>
          </div>
        </div>
      )}

      {/* Condensation Checker */}
      <div className="border-t border-border pt-3">
        <button
          onClick={() => setCondExpanded(!condExpanded)}
          className="text-xs font-semibold text-text-secondary flex items-center gap-1 cursor-pointer"
        >
          <span className={`transform transition-transform ${condExpanded ? "rotate-90" : ""}`}>&#9654;</span>
          Condensation Checker
        </button>

        {condExpanded && (
          <form onSubmit={handleCondCheck} className="flex flex-col gap-3 mt-3">
            <div>
              <label className="block text-xs text-text-muted mb-1">Surface Temp ({tUnit})</label>
              <input
                type="number"
                value={surfaceTemp}
                onChange={(e) => setSurfaceTemp(e.target.value)}
                step={1}
                placeholder="\u2014"
                className={inputClass}
              />
            </div>

            {/* Air state */}
            <div>
              <label className="block text-xs text-text-muted mb-1">Air State</label>
              <select
                value={condPairIndex}
                onChange={(e) => {
                  setCondPairIndex(parseInt(e.target.value));
                  setCondVal1(""); setCondVal2(""); setCondError(null);
                }}
                className={selectClass}
              >
                {INPUT_PAIRS.map((p, i) => (
                  <option key={i} value={i}>{p.label}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">{condLabel1}</label>
                <input type="number" value={condVal1} onChange={(e) => setCondVal1(e.target.value)}
                  step={getFieldStep(condPair[0])} placeholder="\u2014" className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">{condLabel2}</label>
                <input type="number" value={condVal2} onChange={(e) => setCondVal2(e.target.value)}
                  step={getFieldStep(condPair[1])} placeholder="\u2014" className={inputClass} />
              </div>
            </div>

            {/* Auto-fill from state point */}
            {statePoints.length > 0 && (
              <div>
                <label className="block text-xs text-text-muted mb-1">Auto-fill from state point</label>
                <select
                  onChange={(e) => {
                    const idx = parseInt(e.target.value);
                    if (!isNaN(idx)) handleAutoFillCondFromPoint(idx);
                  }}
                  defaultValue=""
                  className={selectClass}
                >
                  <option value="" disabled>Select a point...</option>
                  {statePoints.map((sp, i) => (
                    <option key={i} value={i}>
                      {sp.label || `Point ${i + 1}`} ({fmt(sp.Tdb, 1)}{tUnit}, {fmt(sp.RH, 0)}%)
                    </option>
                  ))}
                </select>
              </div>
            )}

            {condError && (
              <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">{condError}</div>
            )}

            <button
              type="submit"
              disabled={condLoading || !surfaceTemp}
              className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                         rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              {condLoading ? "Checking..." : "Check Condensation"}
            </button>
          </form>
        )}

        {/* Condensation result */}
        {condensationResult && condExpanded && (
          <div className={`mt-3 rounded p-3 text-xs border ${
            condensationResult.is_condensing
              ? "bg-red-400/10 border-red-400/30"
              : "bg-green-400/10 border-green-400/30"
          }`}>
            <div className={`font-semibold mb-1 ${
              condensationResult.is_condensing ? "text-red-400" : "text-green-400"
            }`}>
              {condensationResult.is_condensing ? "Condensation Risk" : "No Condensation"}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-text-primary">
              <span className="text-text-muted">Surface</span>
              <span className="text-right">{fmt(condensationResult.surface_temp, 1)}{tUnit}</span>
              <span className="text-text-muted">Dew Point</span>
              <span className="text-right">{fmt(condensationResult.dew_point, 1)}{tUnit}</span>
              <span className="text-text-muted">Margin</span>
              <span className="text-right">{fmt(condensationResult.margin, 1)}{tUnit}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
