import { useState } from "react";
import { useStore } from "../../store/useStore";
import { calculateSHRLine, calculateGSHR } from "../../api/client";
import { fmt } from "../../utils/formatting";

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

export default function SHRPanel() {
  const { unitSystem, pressure, addSHRLine, shrLines, removeSHRLine, clearSHRLines, setGSHRResult, gshrResult } = useStore();
  const isIP = unitSystem === "IP";
  const tUnit = isIP ? "°F" : "°C";

  // SHR Line form
  const [roomPairIndex, setRoomPairIndex] = useState(0);
  const [roomVal1, setRoomVal1] = useState("");
  const [roomVal2, setRoomVal2] = useState("");
  const [shrValue, setShrValue] = useState("");
  const [shrLoading, setShrLoading] = useState(false);
  const [shrError, setShrError] = useState<string | null>(null);

  // GSHR form
  const [gshrExpanded, setGshrExpanded] = useState(false);
  const [gshrRoomPairIndex, setGshrRoomPairIndex] = useState(0);
  const [gshrRoomVal1, setGshrRoomVal1] = useState("");
  const [gshrRoomVal2, setGshrRoomVal2] = useState("");
  const [oaPairIndex, setOaPairIndex] = useState(0);
  const [oaVal1, setOaVal1] = useState("");
  const [oaVal2, setOaVal2] = useState("");
  const [roomSensible, setRoomSensible] = useState("");
  const [roomTotal, setRoomTotal] = useState("");
  const [oaFraction, setOaFraction] = useState("");
  const [totalAirflow, setTotalAirflow] = useState("");
  const [gshrBF, setGshrBF] = useState("");
  const [gshrLoading, setGshrLoading] = useState(false);
  const [gshrError, setGshrError] = useState<string | null>(null);

  const roomPair = INPUT_PAIRS[roomPairIndex].value;
  const [roomLabel1, roomLabel2] = getFieldLabels(roomPair, unitSystem);

  async function handleSHRLine(e: React.FormEvent) {
    e.preventDefault();
    const v1 = parseFloat(roomVal1);
    const v2 = parseFloat(roomVal2);
    const shr = parseFloat(shrValue);
    if (isNaN(v1) || isNaN(v2)) { setShrError("Enter valid room conditions"); return; }
    if (isNaN(shr) || shr <= 0 || shr > 1) { setShrError("SHR must be between 0 and 1"); return; }

    setShrLoading(true);
    setShrError(null);
    try {
      const result = await calculateSHRLine({
        unit_system: unitSystem,
        pressure,
        room_pair: roomPair,
        room_values: [v1, v2],
        shr,
      });
      addSHRLine(result);
    } catch (e) {
      setShrError(e instanceof Error ? e.message : "SHR line calculation failed");
    } finally {
      setShrLoading(false);
    }
  }

  async function handleGSHR(e: React.FormEvent) {
    e.preventDefault();
    const gshrRoomPair = INPUT_PAIRS[gshrRoomPairIndex].value;
    const rv1 = parseFloat(gshrRoomVal1);
    const rv2 = parseFloat(gshrRoomVal2);
    const oaPair = INPUT_PAIRS[oaPairIndex].value;
    const ov1 = parseFloat(oaVal1);
    const ov2 = parseFloat(oaVal2);
    const qs = parseFloat(roomSensible);
    const qt = parseFloat(roomTotal);
    const oaf = parseFloat(oaFraction);
    const cfm = parseFloat(totalAirflow);

    if (isNaN(rv1) || isNaN(rv2)) { setGshrError("Enter valid room conditions"); return; }
    if (isNaN(ov1) || isNaN(ov2)) { setGshrError("Enter valid OA conditions"); return; }
    if (isNaN(qs) || isNaN(qt) || isNaN(oaf) || isNaN(cfm)) {
      setGshrError("Enter valid loads and airflow"); return;
    }

    const input: Parameters<typeof calculateGSHR>[0] = {
      unit_system: unitSystem,
      pressure,
      room_pair: gshrRoomPair,
      room_values: [rv1, rv2],
      oa_pair: oaPair,
      oa_values: [ov1, ov2],
      room_sensible_load: qs,
      room_total_load: qt,
      oa_fraction: oaf,
      total_airflow: cfm,
    };

    const bf = parseFloat(gshrBF);
    if (!isNaN(bf) && bf > 0 && bf < 1) input.bypass_factor = bf;

    setGshrLoading(true);
    setGshrError(null);
    try {
      const result = await calculateGSHR(input);
      setGSHRResult(result);
    } catch (e) {
      setGshrError(e instanceof Error ? e.message : "GSHR calculation failed");
    } finally {
      setGshrLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Section 1: SHR Line */}
      <form onSubmit={handleSHRLine} className="flex flex-col gap-3">
        <div className="text-xs font-semibold text-text-secondary">Room SHR Line</div>

        <div>
          <label className="block text-xs text-text-muted mb-1">Room State</label>
          <select
            value={roomPairIndex}
            onChange={(e) => { setRoomPairIndex(parseInt(e.target.value)); setRoomVal1(""); setRoomVal2(""); }}
            className={selectClass}
          >
            {INPUT_PAIRS.map((p, i) => (
              <option key={i} value={i}>{p.label}</option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">{roomLabel1}</label>
            <input type="number" value={roomVal1} onChange={(e) => setRoomVal1(e.target.value)}
              step={getFieldStep(roomPair[0])} placeholder="—" className={inputClass} />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">{roomLabel2}</label>
            <input type="number" value={roomVal2} onChange={(e) => setRoomVal2(e.target.value)}
              step={getFieldStep(roomPair[1])} placeholder="—" className={inputClass} />
          </div>
        </div>

        <div>
          <label className="block text-xs text-text-muted mb-1">SHR (0–1)</label>
          <input type="number" value={shrValue} onChange={(e) => setShrValue(e.target.value)}
            min={0} max={1} step={0.01} placeholder="—" className={inputClass} />
        </div>

        {shrError && (
          <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">{shrError}</div>
        )}

        <button
          type="submit"
          disabled={shrLoading || !roomVal1 || !roomVal2 || !shrValue}
          className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                     rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {shrLoading ? "Calculating..." : "Add SHR Line"}
        </button>
      </form>

      {/* SHR Lines list */}
      {shrLines.length > 0 && (
        <div className="flex flex-col gap-2">
          {shrLines.map((line, i) => (
            <div key={i} className="bg-bg-tertiary border border-border rounded p-2 text-xs flex justify-between items-start">
              <div>
                <span className="text-text-primary font-mono">SHR={fmt(line.shr, 2)}</span>
                <span className="text-text-muted ml-2">ADP={fmt(line.adp_Tdb, 1)}{tUnit}</span>
              </div>
              <button
                onClick={() => removeSHRLine(i)}
                className="text-red-400 hover:text-red-300 text-xs ml-2 cursor-pointer"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            onClick={clearSHRLines}
            className="text-xs text-text-muted hover:text-red-400 self-end cursor-pointer"
          >
            Clear all
          </button>
        </div>
      )}

      {/* Section 2: GSHR Calculator */}
      <div className="border-t border-border pt-3">
        <button
          onClick={() => setGshrExpanded(!gshrExpanded)}
          className="text-xs font-semibold text-text-secondary flex items-center gap-1 cursor-pointer"
        >
          <span className={`transform transition-transform ${gshrExpanded ? "rotate-90" : ""}`}>▶</span>
          GSHR / ESHR Calculator
        </button>

        {gshrExpanded && (
          <form onSubmit={handleGSHR} className="flex flex-col gap-3 mt-3">
            {/* Room conditions */}
            <div>
              <label className="block text-xs text-text-muted mb-1">Room State</label>
              <select
                value={gshrRoomPairIndex}
                onChange={(e) => { setGshrRoomPairIndex(parseInt(e.target.value)); setGshrRoomVal1(""); setGshrRoomVal2(""); }}
                className={selectClass}
              >
                {INPUT_PAIRS.map((p, i) => (
                  <option key={i} value={i}>{p.label}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(() => {
                const gPair = INPUT_PAIRS[gshrRoomPairIndex].value;
                const [gl1, gl2] = getFieldLabels(gPair, unitSystem);
                return (
                  <>
                    <div>
                      <label className="block text-xs text-text-muted mb-1">{gl1}</label>
                      <input type="number" value={gshrRoomVal1} onChange={(e) => setGshrRoomVal1(e.target.value)}
                        step={getFieldStep(gPair[0])} placeholder="—" className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted mb-1">{gl2}</label>
                      <input type="number" value={gshrRoomVal2} onChange={(e) => setGshrRoomVal2(e.target.value)}
                        step={getFieldStep(gPair[1])} placeholder="—" className={inputClass} />
                    </div>
                  </>
                );
              })()}
            </div>

            {/* OA conditions */}
            <div>
              <label className="block text-xs text-text-muted mb-1">Outdoor Air</label>
              <select
                value={oaPairIndex}
                onChange={(e) => { setOaPairIndex(parseInt(e.target.value)); setOaVal1(""); setOaVal2(""); }}
                className={selectClass}
              >
                {INPUT_PAIRS.map((p, i) => (
                  <option key={i} value={i}>{p.label}</option>
                ))}
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(() => {
                const oPair = INPUT_PAIRS[oaPairIndex].value;
                const [ol1, ol2] = getFieldLabels(oPair, unitSystem);
                return (
                  <>
                    <div>
                      <label className="block text-xs text-text-muted mb-1">{ol1}</label>
                      <input type="number" value={oaVal1} onChange={(e) => setOaVal1(e.target.value)}
                        step={getFieldStep(oPair[0])} placeholder="—" className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-xs text-text-muted mb-1">{ol2}</label>
                      <input type="number" value={oaVal2} onChange={(e) => setOaVal2(e.target.value)}
                        step={getFieldStep(oPair[1])} placeholder="—" className={inputClass} />
                    </div>
                  </>
                );
              })()}
            </div>

            {/* Room loads */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Qs Room (BTU/hr)" : "Qs Room (W)"}
                </label>
                <input type="number" value={roomSensible} onChange={(e) => setRoomSensible(e.target.value)}
                  step={1000} placeholder="—" className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Qt Room (BTU/hr)" : "Qt Room (W)"}
                </label>
                <input type="number" value={roomTotal} onChange={(e) => setRoomTotal(e.target.value)}
                  step={1000} placeholder="—" className={inputClass} />
              </div>
            </div>

            {/* OA fraction + airflow */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">OA Fraction (0–1)</label>
                <input type="number" value={oaFraction} onChange={(e) => setOaFraction(e.target.value)}
                  min={0} max={1} step={0.05} placeholder="—" className={inputClass} />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Total CFM" : "Total m³/s"}
                </label>
                <input type="number" value={totalAirflow} onChange={(e) => setTotalAirflow(e.target.value)}
                  step={isIP ? 100 : 0.1} placeholder="—" className={inputClass} />
              </div>
            </div>

            {/* Optional BF for ESHR */}
            <div>
              <label className="block text-xs text-text-muted mb-1">BF for ESHR (optional, 0–1)</label>
              <input type="number" value={gshrBF} onChange={(e) => setGshrBF(e.target.value)}
                min={0} max={1} step={0.01} placeholder="—" className={inputClass} />
            </div>

            {gshrError && (
              <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">{gshrError}</div>
            )}

            <button
              type="submit"
              disabled={gshrLoading}
              className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                         rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              {gshrLoading ? "Calculating..." : "Calculate GSHR"}
            </button>
          </form>
        )}

        {/* GSHR Results */}
        {gshrResult && (
          <div className="bg-bg-tertiary border border-border rounded p-3 text-xs mt-3">
            <div className="font-semibold text-text-primary mb-2">GSHR Results</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              <span className="text-text-muted">Room SHR</span>
              <span className="text-text-primary text-right">{fmt(gshrResult.room_shr, 3)}</span>
              <span className="text-text-muted">GSHR</span>
              <span className="text-text-primary text-right">{fmt(gshrResult.gshr, 3)}</span>
              {gshrResult.eshr !== null && (
                <>
                  <span className="text-text-muted">ESHR</span>
                  <span className="text-text-primary text-right">{fmt(gshrResult.eshr, 3)}</span>
                </>
              )}
              <span className="text-text-muted">Room SHR ADP</span>
              <span className="text-text-primary text-right">{fmt(gshrResult.room_shr_adp.Tdb, 1)}{tUnit}</span>
              <span className="text-text-muted">GSHR ADP</span>
              <span className="text-text-primary text-right">{fmt(gshrResult.gshr_adp.Tdb, 1)}{tUnit}</span>
              {gshrResult.eshr_adp && (
                <>
                  <span className="text-text-muted">ESHR ADP</span>
                  <span className="text-text-primary text-right">{fmt(gshrResult.eshr_adp.Tdb, 1)}{tUnit}</span>
                </>
              )}
            </div>
            {gshrResult.warnings.length > 0 && (
              <div className="border-t border-border pt-2 mt-2">
                {gshrResult.warnings.map((w, i) => (
                  <div key={i} className="text-yellow-400 text-xs">{w}</div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
