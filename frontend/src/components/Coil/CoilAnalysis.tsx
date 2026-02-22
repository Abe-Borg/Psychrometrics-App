import { useState } from "react";
import { useStore } from "../../store/useStore";
import { analyzeCoil } from "../../api/client";
import { fmt } from "../../utils/formatting";
import type { CoilMode } from "../../types/psychro";

const INPUT_PAIRS: { value: [string, string]; label: string }[] = [
  { value: ["Tdb", "RH"], label: "Tdb + RH" },
  { value: ["Tdb", "Twb"], label: "Tdb + Twb" },
  { value: ["Tdb", "Tdp"], label: "Tdb + Tdp" },
  { value: ["Tdb", "W"], label: "Tdb + W (lb/lb)" },
  { value: ["Tdb", "h"], label: "Tdb + h" },
  { value: ["Twb", "RH"], label: "Twb + RH" },
  { value: ["Tdp", "RH"], label: "Tdp + RH" },
];

const COIL_MODES: { value: CoilMode; label: string }[] = [
  { value: "forward", label: "Forward (ADP + BF)" },
  { value: "reverse", label: "Reverse (Leaving conditions)" },
];

function getFieldLabels(
  pair: [string, string],
  unitSystem: string
): [string, string] {
  const isIP = unitSystem === "IP";
  const labels: Record<string, string> = {
    Tdb: isIP ? "Dry-Bulb (°F)" : "Dry-Bulb (°C)",
    Twb: isIP ? "Wet-Bulb (°F)" : "Wet-Bulb (°C)",
    Tdp: isIP ? "Dew Point (°F)" : "Dew Point (°C)",
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

const selectClass =
  "w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm text-text-primary focus:outline-none focus:border-accent cursor-pointer";
const inputClass =
  "w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm text-text-primary focus:outline-none focus:border-accent";

export default function CoilAnalysis() {
  const { unitSystem, pressure, setCoilResult, coilResult } = useStore();
  const isIP = unitSystem === "IP";

  // Mode
  const [mode, setMode] = useState<CoilMode>("forward");

  // Entering conditions
  const [enterPairIndex, setEnterPairIndex] = useState(0);
  const [enterVal1, setEnterVal1] = useState("");
  const [enterVal2, setEnterVal2] = useState("");

  // Forward mode
  const [adpTdb, setAdpTdb] = useState("");
  const [bypassFactor, setBypassFactor] = useState("");

  // Reverse mode
  const [leavePairIndex, setLeavePairIndex] = useState(0);
  const [leaveVal1, setLeaveVal1] = useState("");
  const [leaveVal2, setLeaveVal2] = useState("");

  // Optional
  const [airflow, setAirflow] = useState("");
  const [waterEntering, setWaterEntering] = useState("");
  const [waterLeaving, setWaterLeaving] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enterPair = INPUT_PAIRS[enterPairIndex].value;
  const [enterLabel1, enterLabel2] = getFieldLabels(enterPair, unitSystem);
  const leavePair = INPUT_PAIRS[leavePairIndex].value;
  const [leaveLabel1, leaveLabel2] = getFieldLabels(leavePair, unitSystem);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const ev1 = parseFloat(enterVal1);
    const ev2 = parseFloat(enterVal2);
    if (isNaN(ev1) || isNaN(ev2)) {
      setError("Enter valid numbers for the entering conditions");
      return;
    }

    const input: Parameters<typeof analyzeCoil>[0] = {
      mode,
      unit_system: unitSystem,
      pressure,
      entering_pair: enterPair,
      entering_values: [ev1, ev2],
    };

    if (mode === "forward") {
      const a = parseFloat(adpTdb);
      const b = parseFloat(bypassFactor);
      if (isNaN(a) || isNaN(b)) { setError("Enter valid ADP and bypass factor"); return; }
      if (b <= 0 || b >= 1) { setError("Bypass factor must be between 0 and 1"); return; }
      input.adp_Tdb = a;
      input.bypass_factor = b;
    } else {
      const lv1 = parseFloat(leaveVal1);
      const lv2 = parseFloat(leaveVal2);
      if (isNaN(lv1) || isNaN(lv2)) { setError("Enter valid leaving conditions"); return; }
      input.leaving_pair = leavePair;
      input.leaving_values = [lv1, lv2];
    }

    // Optional fields
    const af = parseFloat(airflow);
    if (!isNaN(af) && af > 0) input.airflow = af;

    const we = parseFloat(waterEntering);
    const wl = parseFloat(waterLeaving);
    if (!isNaN(we) && !isNaN(wl)) {
      input.water_entering_temp = we;
      input.water_leaving_temp = wl;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await analyzeCoil(input);
      setCoilResult(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Coil analysis failed");
    } finally {
      setLoading(false);
    }
  }

  const tUnit = isIP ? "°F" : "°C";

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        {/* Mode */}
        <div>
          <label className="block text-xs text-text-muted mb-1">Mode</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as CoilMode)}
            className={selectClass}
          >
            {COIL_MODES.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
        </div>

        {/* Entering conditions */}
        <div>
          <label className="block text-xs text-text-muted mb-1">Entering Air</label>
          <select
            value={enterPairIndex}
            onChange={(e) => {
              setEnterPairIndex(parseInt(e.target.value));
              setEnterVal1(""); setEnterVal2(""); setError(null);
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
            <label className="block text-xs text-text-muted mb-1">{enterLabel1}</label>
            <input type="number" value={enterVal1} onChange={(e) => setEnterVal1(e.target.value)}
              step={getFieldStep(enterPair[0])} placeholder="—" className={inputClass} />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">{enterLabel2}</label>
            <input type="number" value={enterVal2} onChange={(e) => setEnterVal2(e.target.value)}
              step={getFieldStep(enterPair[1])} placeholder="—" className={inputClass} />
          </div>
        </div>

        {/* Forward mode: ADP + BF */}
        {mode === "forward" && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-xs text-text-muted mb-1">ADP Tdb ({tUnit})</label>
              <input type="number" value={adpTdb} onChange={(e) => setAdpTdb(e.target.value)}
                step={1} placeholder="—" className={inputClass} />
            </div>
            <div>
              <label className="block text-xs text-text-muted mb-1">BF (0–1)</label>
              <input type="number" value={bypassFactor} onChange={(e) => setBypassFactor(e.target.value)}
                min={0} max={1} step={0.01} placeholder="—" className={inputClass} />
            </div>
          </div>
        )}

        {/* Reverse mode: leaving conditions */}
        {mode === "reverse" && (
          <>
            <div>
              <label className="block text-xs text-text-muted mb-1">Leaving Air</label>
              <select
                value={leavePairIndex}
                onChange={(e) => {
                  setLeavePairIndex(parseInt(e.target.value));
                  setLeaveVal1(""); setLeaveVal2(""); setError(null);
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
                <label className="block text-xs text-text-muted mb-1">{leaveLabel1}</label>
                <input type="number" value={leaveVal1} onChange={(e) => setLeaveVal1(e.target.value)}
                  step={getFieldStep(leavePair[0])} placeholder="—" className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">{leaveLabel2}</label>
                <input type="number" value={leaveVal2} onChange={(e) => setLeaveVal2(e.target.value)}
                  step={getFieldStep(leavePair[1])} placeholder="—" className={inputClass} />
              </div>
            </div>
          </>
        )}

        {/* Optional: Airflow */}
        <div>
          <label className="block text-xs text-text-muted mb-1">
            {isIP ? "Airflow (CFM) — optional" : "Airflow (m³/s) — optional"}
          </label>
          <input type="number" value={airflow} onChange={(e) => setAirflow(e.target.value)}
            step={isIP ? 10 : 0.01} placeholder="—" className={inputClass} />
        </div>

        {/* Optional: Water temps */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">Water In ({tUnit})</label>
            <input type="number" value={waterEntering} onChange={(e) => setWaterEntering(e.target.value)}
              step={1} placeholder="—" className={inputClass} />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Water Out ({tUnit})</label>
            <input type="number" value={waterLeaving} onChange={(e) => setWaterLeaving(e.target.value)}
              step={1} placeholder="—" className={inputClass} />
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">
            {error}
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={loading || !enterVal1 || !enterVal2}
          className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                     rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {loading ? "Analyzing..." : "Analyze Coil"}
        </button>
      </form>

      {/* Results */}
      {coilResult && (
        <div className="bg-bg-tertiary border border-border rounded p-3 text-xs">
          <div className="font-semibold text-text-primary mb-2">Coil Analysis Results</div>

          {/* Key values */}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2">
            <span className="text-text-muted">ADP Tdb</span>
            <span className="text-text-primary text-right">{fmt(coilResult.adp.Tdb, 1)}{tUnit}</span>
            <span className="text-text-muted">BF</span>
            <span className="text-text-primary text-right">{fmt(coilResult.bypass_factor, 3)}</span>
            <span className="text-text-muted">CF</span>
            <span className="text-text-primary text-right">{fmt(coilResult.contact_factor, 3)}</span>
          </div>

          {/* Load breakdown */}
          <div className="border-t border-border pt-2 mt-2">
            <div className="font-semibold text-text-secondary mb-1">Loads ({coilResult.load_unit})</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <span className="text-text-muted">Qs (sensible)</span>
              <span className="text-text-primary text-right">{fmt(coilResult.Qs, 2)}</span>
              <span className="text-text-muted">Ql (latent)</span>
              <span className="text-text-primary text-right">{fmt(coilResult.Ql, 2)}</span>
              <span className="text-text-muted">Qt (total)</span>
              <span className="text-text-primary text-right">{fmt(coilResult.Qt, 2)}</span>
              <span className="text-text-muted">SHR</span>
              <span className="text-text-primary text-right">{fmt(coilResult.SHR, 3)}</span>
            </div>
          </div>

          {/* GPM */}
          {coilResult.gpm !== null && (
            <div className="border-t border-border pt-2 mt-2">
              <div className="grid grid-cols-2 gap-x-4">
                <span className="text-text-muted">{isIP ? "GPM" : "L/s"}</span>
                <span className="text-text-primary text-right">{fmt(coilResult.gpm, 2)}</span>
              </div>
            </div>
          )}

          {/* Warnings */}
          {coilResult.warnings.length > 0 && (
            <div className="border-t border-border pt-2 mt-2">
              {coilResult.warnings.map((w, i) => (
                <div key={i} className="text-yellow-400 text-xs">{w}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
