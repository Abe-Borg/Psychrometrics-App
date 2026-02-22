import { useState } from "react";
import { useStore } from "../../store/useStore";
import { calculateAHUWizard } from "../../api/client";
import type { AHUType, AHUWizardInput, AHUWizardOutput } from "../../types/psychro";

const AHU_TYPES: { value: AHUType; label: string; desc: string }[] = [
  { value: "mixed_air", label: "Mixed Air", desc: "OA + RA mixing box" },
  { value: "full_oa", label: "100% Outside Air", desc: "DOAS / no return air" },
  { value: "economizer", label: "Economizer", desc: "Variable OA fraction" },
];

const STEPS = ["AHU Type", "Outside Air", "Return Air", "Mixing", "Supply Target", "Calculate"];

export default function AHUWizard() {
  const {
    unitSystem, pressure,
    ahuWizardResult, ahuWizardLoading,
    setAHUWizardResult, clearAHUWizardResult,
    setAHUWizardLoading, applyAHUWizardToChart,
    designDayResult,
    addToast,
  } = useStore();

  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [ahuType, setAHUType] = useState<AHUType>("mixed_air");
  const [oaTdb, setOaTdb] = useState("");
  const [oaCoincident, setOaCoincident] = useState("");
  const [oaInputType, setOaInputType] = useState<"Twb" | "RH">("Twb");
  const [raTdb, setRaTdb] = useState("75");
  const [raRH, setRaRH] = useState("50");
  const [oaFraction, setOaFraction] = useState("0.3");
  const [supplyTdb, setSupplyTdb] = useState("55");
  const [supplyRH, setSupplyRH] = useState("");
  const [roomSensibleLoad, setRoomSensibleLoad] = useState("");

  const isIP = unitSystem === "IP";
  const needsRA = ahuType === "mixed_air" || ahuType === "economizer";

  // Pre-fill from design day cooling conditions
  const handlePrefillFromDesignDay = () => {
    if (!designDayResult?.points?.length) return;
    const coolingPt = designDayResult.points.find(
      (p) => p.category === "cooling_db"
    );
    if (coolingPt) {
      setOaTdb(coolingPt.Tdb.toString());
      setOaCoincident(coolingPt.Twb.toString());
      setOaInputType("Twb");
    }
  };

  // Determine active step (skip RA/Mixing for full_oa)
  const activeSteps = needsRA
    ? STEPS
    : [STEPS[0], STEPS[1], STEPS[4], STEPS[5]];

  const currentStepLabel = activeSteps[step] || "";

  const canGoNext = () => {
    if (currentStepLabel === "AHU Type") return true;
    if (currentStepLabel === "Outside Air") return oaTdb !== "" && oaCoincident !== "";
    if (currentStepLabel === "Return Air") return raTdb !== "" && raRH !== "";
    if (currentStepLabel === "Mixing") return oaFraction !== "";
    if (currentStepLabel === "Supply Target") return supplyTdb !== "";
    return true;
  };

  const handleNext = () => {
    if (step < activeSteps.length - 1) setStep(step + 1);
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleCalculate = async () => {
    setError(null);
    setAHUWizardLoading(true);

    const input: AHUWizardInput = {
      ahu_type: ahuType,
      unit_system: unitSystem,
      pressure,
      oa_Tdb: parseFloat(oaTdb),
      oa_coincident: parseFloat(oaCoincident),
      oa_input_type: oaInputType,
      supply_Tdb: parseFloat(supplyTdb),
    };

    if (needsRA) {
      input.ra_Tdb = parseFloat(raTdb);
      input.ra_RH = parseFloat(raRH);
      input.oa_fraction = parseFloat(oaFraction);
    }

    if (supplyRH) input.supply_RH = parseFloat(supplyRH);
    if (roomSensibleLoad) input.room_sensible_load = parseFloat(roomSensibleLoad);

    try {
      const result = await calculateAHUWizard(input);
      setAHUWizardResult(result);
      addToast("AHU wizard calculation complete", "success");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      addToast("AHU wizard failed", "error");
    } finally {
      setAHUWizardLoading(false);
    }
  };

  const handleApplyToChart = () => {
    applyAHUWizardToChart();
    addToast("AHU wizard results applied to chart", "success");
  };

  const handleClear = () => {
    clearAHUWizardResult();
    setStep(0);
    setError(null);
  };

  const fmt = (v: number, decimals = 1) => v.toFixed(decimals);

  // ── Render result summary ──
  if (ahuWizardResult) {
    return <ResultView result={ahuWizardResult} onApply={handleApplyToChart} onClear={handleClear} fmt={fmt} isIP={isIP} />;
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Step indicator */}
      <div className="flex gap-1">
        {activeSteps.map((s, i) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded ${
              i <= step ? "bg-accent" : "bg-bg-primary"
            }`}
          />
        ))}
      </div>
      <p className="text-xs text-text-secondary">
        Step {step + 1}/{activeSteps.length}: {currentStepLabel}
      </p>

      {/* Step content */}
      {currentStepLabel === "AHU Type" && (
        <div className="flex flex-col gap-2">
          {AHU_TYPES.map((t) => (
            <label key={t.value} className="flex items-start gap-2 text-xs cursor-pointer">
              <input
                type="radio"
                name="ahuType"
                value={t.value}
                checked={ahuType === t.value}
                onChange={() => setAHUType(t.value)}
                className="mt-0.5 accent-accent"
              />
              <div>
                <span className="text-text-primary font-medium">{t.label}</span>
                <span className="text-text-secondary ml-1">— {t.desc}</span>
              </div>
            </label>
          ))}
        </div>
      )}

      {currentStepLabel === "Outside Air" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Tdb ({isIP ? "°F" : "°C"})</label>
            <input
              type="number"
              value={oaTdb}
              onChange={(e) => setOaTdb(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder={isIP ? "95" : "35"}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">
              {oaInputType === "Twb" ? `Twb (${isIP ? "°F" : "°C"})` : "RH (%)"}
            </label>
            <input
              type="number"
              value={oaCoincident}
              onChange={(e) => setOaCoincident(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder={oaInputType === "Twb" ? (isIP ? "78" : "26") : "50"}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Input type</label>
            <select
              value={oaInputType}
              onChange={(e) => setOaInputType(e.target.value as "Twb" | "RH")}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
            >
              <option value="Twb">Wet-Bulb</option>
              <option value="RH">Relative Humidity</option>
            </select>
          </div>
          {designDayResult && designDayResult.points.length > 0 && (
            <button
              onClick={handlePrefillFromDesignDay}
              className="text-xs text-accent hover:underline cursor-pointer text-left"
            >
              Pre-fill from design day data
            </button>
          )}
        </div>
      )}

      {currentStepLabel === "Return Air" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Tdb ({isIP ? "°F" : "°C"})</label>
            <input
              type="number"
              value={raTdb}
              onChange={(e) => setRaTdb(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder={isIP ? "75" : "24"}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">RH (%)</label>
            <input
              type="number"
              value={raRH}
              onChange={(e) => setRaRH(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder="50"
            />
          </div>
        </div>
      )}

      {currentStepLabel === "Mixing" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">OA Fraction</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={oaFraction}
              onChange={(e) => setOaFraction(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder="0.3"
            />
          </div>
          <p className="text-xs text-text-secondary">
            OA fraction: ratio of outside air mass flow to total supply air (0-1).
            30% OA is typical for many comfort applications.
          </p>
        </div>
      )}

      {currentStepLabel === "Supply Target" && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Supply Tdb ({isIP ? "°F" : "°C"})</label>
            <input
              type="number"
              value={supplyTdb}
              onChange={(e) => setSupplyTdb(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder={isIP ? "55" : "13"}
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Supply RH (%)</label>
            <input
              type="number"
              value={supplyRH}
              onChange={(e) => setSupplyRH(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder="Optional"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-text-secondary w-20">Qs room ({isIP ? "BTU/hr" : "W"})</label>
            <input
              type="number"
              value={roomSensibleLoad}
              onChange={(e) => setRoomSensibleLoad(e.target.value)}
              className="flex-1 bg-bg-primary border border-border rounded px-2 py-1 text-xs text-text-primary"
              placeholder="Optional — for airflow sizing"
            />
          </div>
        </div>
      )}

      {currentStepLabel === "Calculate" && (
        <div className="flex flex-col gap-2 text-xs text-text-secondary">
          <p className="font-medium text-text-primary">Review</p>
          <p>AHU Type: {AHU_TYPES.find((t) => t.value === ahuType)?.label}</p>
          <p>OA: {oaTdb}{isIP ? "°F" : "°C"} / {oaInputType === "Twb" ? "Twb" : "RH"} {oaCoincident}{oaInputType === "Twb" ? (isIP ? "°F" : "°C") : "%"}</p>
          {needsRA && <p>RA: {raTdb}{isIP ? "°F" : "°C"} / {raRH}% RH</p>}
          {needsRA && <p>OA Fraction: {oaFraction}</p>}
          <p>Supply Target: {supplyTdb}{isIP ? "°F" : "°C"}{supplyRH ? ` / ${supplyRH}% RH` : ""}</p>
          {roomSensibleLoad && <p>Room Qs: {roomSensibleLoad} {isIP ? "BTU/hr" : "W"}</p>}
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400 break-words">{error}</p>
      )}

      {/* Navigation */}
      <div className="flex gap-2 mt-1">
        {step > 0 && (
          <button
            onClick={handleBack}
            className="px-3 py-1 text-xs border border-border rounded text-text-secondary hover:text-text-primary cursor-pointer"
          >
            Back
          </button>
        )}
        {currentStepLabel !== "Calculate" ? (
          <button
            onClick={handleNext}
            disabled={!canGoNext()}
            className="px-3 py-1 text-xs bg-accent text-white rounded disabled:opacity-40 cursor-pointer"
          >
            Next
          </button>
        ) : (
          <button
            onClick={handleCalculate}
            disabled={ahuWizardLoading}
            className="px-3 py-1 text-xs bg-accent text-white rounded disabled:opacity-40 cursor-pointer"
          >
            {ahuWizardLoading ? "Calculating..." : "Calculate"}
          </button>
        )}
      </div>
    </div>
  );
}

// ── Result sub-component ──

function ResultView({
  result,
  onApply,
  onClear,
  fmt,
  isIP,
}: {
  result: AHUWizardOutput;
  onApply: () => void;
  onClear: () => void;
  fmt: (v: number, d?: number) => string;
  isIP: boolean;
}) {
  const tempUnit = isIP ? "°F" : "°C";
  const loadUnit = isIP ? "BTU/lb" : "kJ/kg";

  return (
    <div className="flex flex-col gap-3 text-xs">
      <p className="font-medium text-text-primary">
        AHU Wizard Results
        <span className="ml-2 text-text-secondary font-normal">
          ({result.ahu_type.replace("_", " ")})
        </span>
      </p>

      {/* State points summary */}
      <div className="flex flex-col gap-1">
        <Row label="OA" tdb={result.oa_point.Tdb} w={result.oa_point.W_display} unit={tempUnit} isIP={isIP} fmt={fmt} />
        {result.ra_point && (
          <Row label="RA" tdb={result.ra_point.Tdb} w={result.ra_point.W_display} unit={tempUnit} isIP={isIP} fmt={fmt} />
        )}
        {result.mixed_point && (
          <Row label="Mix" tdb={result.mixed_point.Tdb} w={result.mixed_point.W_display} unit={tempUnit} isIP={isIP} fmt={fmt} />
        )}
        <Row label="Coil Lvg" tdb={result.coil_leaving.Tdb} w={result.coil_leaving.W_display} unit={tempUnit} isIP={isIP} fmt={fmt} />
        {result.needs_reheat && (
          <Row label="Supply" tdb={result.supply_point.Tdb} w={result.supply_point.W_display} unit={tempUnit} isIP={isIP} fmt={fmt} />
        )}
      </div>

      {/* Loads */}
      <div className="bg-bg-primary border border-border rounded p-2">
        <p className="text-text-secondary mb-1">Cooling Loads ({loadUnit})</p>
        <div className="grid grid-cols-3 gap-1 text-text-primary">
          <span>Qs: {fmt(result.cooling_Qs, 2)}</span>
          <span>Ql: {fmt(result.cooling_Ql, 2)}</span>
          <span>Qt: {fmt(result.cooling_Qt, 2)}</span>
        </div>
        <p className="text-text-secondary mt-1">SHR: {fmt(result.shr, 3)}</p>
        {result.reheat_Q != null && (
          <p className="text-text-secondary">Reheat: {fmt(result.reheat_Q, 2)} {loadUnit}</p>
        )}
        {result.supply_cfm != null && (
          <p className="text-text-secondary">
            Supply airflow: {fmt(result.supply_cfm, 0)} {isIP ? "CFM" : "m³/s"}
          </p>
        )}
      </div>

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="text-yellow-400">
          {result.warnings.map((w, i) => (
            <p key={i}>{w}</p>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onApply}
          className="px-3 py-1 text-xs bg-accent text-white rounded cursor-pointer"
        >
          Apply to Chart
        </button>
        <button
          onClick={onClear}
          className="px-3 py-1 text-xs border border-border rounded text-text-secondary hover:text-text-primary cursor-pointer"
        >
          Clear
        </button>
      </div>
    </div>
  );
}

function Row({
  label,
  tdb,
  w,
  unit,
  isIP,
  fmt,
}: {
  label: string;
  tdb: number;
  w: number;
  unit: string;
  isIP: boolean;
  fmt: (v: number, d?: number) => string;
}) {
  return (
    <div className="flex justify-between text-text-secondary">
      <span className="text-text-primary w-16">{label}</span>
      <span>{fmt(tdb)}{unit}</span>
      <span>{fmt(w, 1)} {isIP ? "gr/lb" : "g/kg"}</span>
    </div>
  );
}
