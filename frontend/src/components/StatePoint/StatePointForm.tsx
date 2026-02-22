import { useState, useEffect } from "react";
import { useStore } from "../../store/useStore";
import { resolveStatePoint } from "../../api/client";

const INPUT_PAIRS: { value: [string, string]; label: string }[] = [
  { value: ["Tdb", "RH"], label: "Tdb + RH" },
  { value: ["Tdb", "Twb"], label: "Tdb + Twb" },
  { value: ["Tdb", "Tdp"], label: "Tdb + Tdp" },
  { value: ["Tdb", "W"], label: "Tdb + W (lb/lb)" },
  { value: ["Tdb", "h"], label: "Tdb + h" },
  { value: ["Twb", "RH"], label: "Twb + RH" },
  { value: ["Tdp", "RH"], label: "Tdp + RH" },
];

// Index of "Tdb + W" pair for click-to-add
const TDB_W_PAIR_INDEX = 3;

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

export default function StatePointForm() {
  const { unitSystem, pressure, addStatePoint, pendingClickPoint, setPendingClickPoint, addToast } = useStore();
  const [pairIndex, setPairIndex] = useState(0);
  const [val1, setVal1] = useState("");
  const [val2, setVal2] = useState("");
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle click-to-add: auto-fill from chart click
  useEffect(() => {
    if (pendingClickPoint) {
      const isIP = unitSystem === "IP";
      // Convert W_display (gr/lb or g/kg) back to lb/lb or kg/kg
      const wRaw = isIP
        ? pendingClickPoint.W_display / 7000
        : pendingClickPoint.W_display / 1000;

      setPairIndex(TDB_W_PAIR_INDEX);
      setVal1(pendingClickPoint.Tdb.toFixed(1));
      setVal2(wRaw.toFixed(6));
      setError(null);
      setPendingClickPoint(null);
    }
  }, [pendingClickPoint]);

  const pair = INPUT_PAIRS[pairIndex].value;
  const [label1, label2] = getFieldLabels(pair, unitSystem);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const v1 = parseFloat(val1);
    const v2 = parseFloat(val2);
    if (isNaN(v1) || isNaN(v2)) {
      setError("Enter valid numbers for both fields");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await resolveStatePoint({
        input_pair: pair,
        values: [v1, v2],
        pressure,
        unit_system: unitSystem,
        label: label || "",
      });
      addStatePoint(result);
      addToast(`Point "${result.label || "P" + (useStore.getState().statePoints.length)}" added`, "success");
      // Reset form but keep pair selection
      setVal1("");
      setVal2("");
      setLabel("");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Calculation failed";
      setError(msg);
      addToast(msg, "error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {/* Input pair selector */}
      <div>
        <label className="block text-xs text-text-muted mb-1">Input Pair</label>
        <select
          value={pairIndex}
          onChange={(e) => {
            setPairIndex(parseInt(e.target.value));
            setVal1("");
            setVal2("");
            setError(null);
          }}
          className="w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm
                     text-text-primary focus:outline-none focus:border-accent cursor-pointer"
        >
          {INPUT_PAIRS.map((p, i) => (
            <option key={i} value={i}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Value inputs — side by side */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-text-muted mb-1">{label1}</label>
          <input
            type="number"
            value={val1}
            onChange={(e) => setVal1(e.target.value)}
            step={getFieldStep(pair[0])}
            placeholder="—"
            className="w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm
                       text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
        <div>
          <label className="block text-xs text-text-muted mb-1">{label2}</label>
          <input
            type="number"
            value={val2}
            onChange={(e) => setVal2(e.target.value)}
            step={getFieldStep(pair[1])}
            placeholder="—"
            className="w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm
                       text-text-primary focus:outline-none focus:border-accent"
          />
        </div>
      </div>

      {/* Label */}
      <div>
        <label className="block text-xs text-text-muted mb-1">Label (optional)</label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Room, OA, Supply"
          maxLength={30}
          className="w-full px-2 py-1.5 bg-bg-tertiary border border-border rounded text-sm
                     text-text-primary focus:outline-none focus:border-accent"
        />
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
        disabled={loading || !val1 || !val2}
        className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                   rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
      >
        {loading ? "Calculating..." : "Add Point"}
      </button>
    </form>
  );
}
