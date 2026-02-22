import { useState } from "react";
import { useStore } from "../../store/useStore";
import { calculateProcess } from "../../api/client";
import type { ProcessType, SensibleMode, CoolingDehumMode, HumidificationMode, DehumidificationMode } from "../../types/psychro";

const PROCESS_TYPES: { value: ProcessType; label: string }[] = [
  { value: "sensible_heating", label: "Sensible Heating" },
  { value: "sensible_cooling", label: "Sensible Cooling" },
  { value: "cooling_dehumidification", label: "Cooling & Dehumidification" },
  { value: "adiabatic_mixing", label: "Adiabatic Mixing" },
  { value: "steam_humidification", label: "Steam Humidification" },
  { value: "adiabatic_humidification", label: "Adiabatic Humidification" },
  { value: "heated_water_humidification", label: "Heated Water Spray" },
  { value: "direct_evaporative", label: "Direct Evaporative" },
  { value: "indirect_evaporative", label: "Indirect Evaporative" },
  { value: "indirect_direct_evaporative", label: "Indirect-Direct (Two-Stage)" },
  { value: "chemical_dehumidification", label: "Chemical Dehumidification" },
  { value: "sensible_reheat", label: "Sensible Reheat" },
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

const SENSIBLE_MODES: { value: SensibleMode; label: string }[] = [
  { value: "target_tdb", label: "Target Tdb" },
  { value: "delta_t", label: "Delta T" },
  { value: "heat_and_airflow", label: "Q + Airflow" },
];

const COOLING_MODES: { value: CoolingDehumMode; label: string }[] = [
  { value: "forward", label: "Forward (ADP + BF)" },
  { value: "reverse", label: "Reverse (Leaving conditions)" },
];

const STEAM_MODES: { value: HumidificationMode; label: string }[] = [
  { value: "target_rh", label: "Target RH" },
  { value: "target_w", label: "Target W" },
];

const ADIABATIC_HUMID_MODES: { value: HumidificationMode; label: string }[] = [
  { value: "effectiveness", label: "Effectiveness" },
  { value: "target_rh", label: "Target RH" },
];

const CHEM_DEHUM_MODES: { value: DehumidificationMode; label: string }[] = [
  { value: "target_w", label: "Target W" },
  { value: "target_rh", label: "Target RH" },
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

export default function ProcessBuilder() {
  const { unitSystem, pressure, addProcess } = useStore();
  const isIP = unitSystem === "IP";

  // Process type
  const [processType, setProcessType] = useState<ProcessType>("sensible_heating");

  // Start point
  const [startPairIndex, setStartPairIndex] = useState(0);
  const [startVal1, setStartVal1] = useState("");
  const [startVal2, setStartVal2] = useState("");

  // Sensible mode
  const [sensibleMode, setSensibleMode] = useState<SensibleMode>("target_tdb");
  const [targetTdb, setTargetTdb] = useState("");
  const [deltaT, setDeltaT] = useState("");
  const [qSensible, setQSensible] = useState("");
  const [airflowCfm, setAirflowCfm] = useState("");

  // Cooling/dehum mode
  const [coolingMode, setCoolingMode] = useState<CoolingDehumMode>("forward");
  const [adpTdb, setAdpTdb] = useState("");
  const [bypassFactor, setBypassFactor] = useState("");
  const [leavingTdb, setLeavingTdb] = useState("");
  const [leavingRH, setLeavingRH] = useState("");

  // Mixing
  const [stream2PairIndex, setStream2PairIndex] = useState(0);
  const [stream2Val1, setStream2Val1] = useState("");
  const [stream2Val2, setStream2Val2] = useState("");
  const [mixingFraction, setMixingFraction] = useState("");

  // Humidification
  const [humidMode, setHumidMode] = useState<HumidificationMode>("target_rh");
  const [targetRH, setTargetRH] = useState("");
  const [targetW, setTargetW] = useState("");
  const [effectiveness, setEffectiveness] = useState("");
  const [waterTemperature, setWaterTemperature] = useState("");

  // Evaporative cooling
  const [iecEffectiveness, setIecEffectiveness] = useState("");
  const [decEffectiveness, setDecEffectiveness] = useState("");

  // Chemical dehumidification
  const [dehumMode, setDehumMode] = useState<DehumidificationMode>("target_w");

  // General
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startPair = INPUT_PAIRS[startPairIndex].value;
  const [startLabel1, startLabel2] = getFieldLabels(startPair, unitSystem);

  const isSensible = processType === "sensible_heating" || processType === "sensible_cooling" || processType === "sensible_reheat";

  function resetProcessFields() {
    setSensibleMode("target_tdb");
    setTargetTdb("");
    setDeltaT("");
    setQSensible("");
    setAirflowCfm("");
    setCoolingMode("forward");
    setAdpTdb("");
    setBypassFactor("");
    setLeavingTdb("");
    setLeavingRH("");
    setStream2PairIndex(0);
    setStream2Val1("");
    setStream2Val2("");
    setMixingFraction("");
    setHumidMode("target_rh");
    setTargetRH("");
    setTargetW("");
    setEffectiveness("");
    setWaterTemperature("");
    setIecEffectiveness("");
    setDecEffectiveness("");
    setDehumMode("target_w");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const sv1 = parseFloat(startVal1);
    const sv2 = parseFloat(startVal2);
    if (isNaN(sv1) || isNaN(sv2)) {
      setError("Enter valid numbers for the start point");
      return;
    }

    const input: Parameters<typeof calculateProcess>[0] = {
      process_type: processType,
      unit_system: unitSystem,
      pressure,
      start_point_pair: startPair,
      start_point_values: [sv1, sv2],
    };

    // Process-specific fields
    if (isSensible) {
      input.sensible_mode = sensibleMode;
      if (sensibleMode === "target_tdb") {
        const t = parseFloat(targetTdb);
        if (isNaN(t)) { setError("Enter a valid target temperature"); return; }
        input.target_Tdb = t;
      } else if (sensibleMode === "delta_t") {
        const d = parseFloat(deltaT);
        if (isNaN(d)) { setError("Enter a valid temperature difference"); return; }
        input.delta_T = d;
      } else {
        const q = parseFloat(qSensible);
        const cfm = parseFloat(airflowCfm);
        if (isNaN(q) || isNaN(cfm)) { setError("Enter valid Q and airflow values"); return; }
        input.Q_sensible = q;
        input.airflow_cfm = cfm;
      }
    } else if (processType === "cooling_dehumidification") {
      input.cooling_dehum_mode = coolingMode;
      if (coolingMode === "forward") {
        const a = parseFloat(adpTdb);
        const b = parseFloat(bypassFactor);
        if (isNaN(a) || isNaN(b)) { setError("Enter valid ADP and bypass factor"); return; }
        if (b <= 0 || b >= 1) { setError("Bypass factor must be between 0 and 1 (exclusive)"); return; }
        input.adp_Tdb = a;
        input.bypass_factor = b;
      } else {
        const lt = parseFloat(leavingTdb);
        const lr = parseFloat(leavingRH);
        if (isNaN(lt) || isNaN(lr)) { setError("Enter valid leaving conditions"); return; }
        input.leaving_Tdb = lt;
        input.leaving_RH = lr;
      }
    } else if (processType === "adiabatic_mixing") {
      const s2v1 = parseFloat(stream2Val1);
      const s2v2 = parseFloat(stream2Val2);
      const mf = parseFloat(mixingFraction);
      if (isNaN(s2v1) || isNaN(s2v2) || isNaN(mf)) {
        setError("Enter valid stream 2 values and mixing fraction");
        return;
      }
      if (mf < 0 || mf > 1) { setError("Mixing fraction must be between 0 and 1"); return; }
      input.stream2_point_pair = INPUT_PAIRS[stream2PairIndex].value;
      input.stream2_point_values = [s2v1, s2v2];
      input.mixing_fraction = mf;
    } else if (processType === "steam_humidification") {
      input.humidification_mode = humidMode;
      if (humidMode === "target_rh") {
        const rh = parseFloat(targetRH);
        if (isNaN(rh)) { setError("Enter a valid target RH"); return; }
        input.target_RH = rh;
      } else if (humidMode === "target_w") {
        const w = parseFloat(targetW);
        if (isNaN(w)) { setError("Enter a valid target W"); return; }
        input.target_W = w;
      }
    } else if (processType === "adiabatic_humidification") {
      input.humidification_mode = humidMode;
      if (humidMode === "effectiveness") {
        const eff = parseFloat(effectiveness);
        if (isNaN(eff)) { setError("Enter a valid effectiveness"); return; }
        if (eff < 0 || eff > 1) { setError("Effectiveness must be between 0 and 1"); return; }
        input.effectiveness = eff;
      } else if (humidMode === "target_rh") {
        const rh = parseFloat(targetRH);
        if (isNaN(rh)) { setError("Enter a valid target RH"); return; }
        input.target_RH = rh;
      }
    } else if (processType === "heated_water_humidification") {
      const eff = parseFloat(effectiveness);
      const wt = parseFloat(waterTemperature);
      if (isNaN(eff) || isNaN(wt)) { setError("Enter valid effectiveness and water temperature"); return; }
      if (eff < 0 || eff > 1) { setError("Effectiveness must be between 0 and 1"); return; }
      input.effectiveness = eff;
      input.water_temperature = wt;
    } else if (processType === "direct_evaporative") {
      const eff = parseFloat(effectiveness);
      if (isNaN(eff)) { setError("Enter a valid effectiveness"); return; }
      if (eff < 0 || eff > 1) { setError("Effectiveness must be between 0 and 1"); return; }
      input.effectiveness = eff;
    } else if (processType === "indirect_evaporative") {
      const eff = parseFloat(effectiveness);
      if (isNaN(eff)) { setError("Enter a valid effectiveness"); return; }
      if (eff < 0 || eff > 1) { setError("Effectiveness must be between 0 and 1"); return; }
      input.effectiveness = eff;
    } else if (processType === "indirect_direct_evaporative") {
      const ie = parseFloat(iecEffectiveness);
      const de = parseFloat(decEffectiveness);
      if (isNaN(ie) || isNaN(de)) { setError("Enter valid IEC and DEC effectiveness values"); return; }
      if (ie < 0 || ie > 1 || de < 0 || de > 1) { setError("Effectiveness must be between 0 and 1"); return; }
      input.iec_effectiveness = ie;
      input.dec_effectiveness = de;
    } else if (processType === "chemical_dehumidification") {
      input.dehum_mode = dehumMode;
      if (dehumMode === "target_w") {
        const w = parseFloat(targetW);
        if (isNaN(w)) { setError("Enter a valid target W"); return; }
        input.target_W = w;
      } else if (dehumMode === "target_rh") {
        const rh = parseFloat(targetRH);
        if (isNaN(rh)) { setError("Enter a valid target RH"); return; }
        input.target_RH = rh;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const result = await calculateProcess(input);
      addProcess(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Process calculation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      {/* Process type selector */}
      <div>
        <label className="block text-xs text-text-muted mb-1">Process Type</label>
        <select
          value={processType}
          onChange={(e) => {
            setProcessType(e.target.value as ProcessType);
            resetProcessFields();
          }}
          className={selectClass}
        >
          {PROCESS_TYPES.map((p) => (
            <option key={p.value} value={p.value}>
              {p.label}
            </option>
          ))}
        </select>
      </div>

      {/* Start point */}
      <div>
        <label className="block text-xs text-text-muted mb-1">Start Point</label>
        <select
          value={startPairIndex}
          onChange={(e) => {
            setStartPairIndex(parseInt(e.target.value));
            setStartVal1("");
            setStartVal2("");
            setError(null);
          }}
          className={selectClass}
        >
          {INPUT_PAIRS.map((p, i) => (
            <option key={i} value={i}>
              {p.label}
            </option>
          ))}
        </select>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="block text-xs text-text-muted mb-1">{startLabel1}</label>
          <input
            type="number"
            value={startVal1}
            onChange={(e) => setStartVal1(e.target.value)}
            step={getFieldStep(startPair[0])}
            placeholder="—"
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-xs text-text-muted mb-1">{startLabel2}</label>
          <input
            type="number"
            value={startVal2}
            onChange={(e) => setStartVal2(e.target.value)}
            step={getFieldStep(startPair[1])}
            placeholder="—"
            className={inputClass}
          />
        </div>
      </div>

      {/* --- Sensible heating / cooling parameters --- */}
      {isSensible && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Mode</label>
            <select
              value={sensibleMode}
              onChange={(e) => setSensibleMode(e.target.value as SensibleMode)}
              className={selectClass}
            >
              {SENSIBLE_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {sensibleMode === "target_tdb" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">
                {isIP ? "Target Tdb (°F)" : "Target Tdb (°C)"}
              </label>
              <input
                type="number"
                value={targetTdb}
                onChange={(e) => setTargetTdb(e.target.value)}
                step={1}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}

          {sensibleMode === "delta_t" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">
                {isIP ? "Delta T (°F)" : "Delta T (°C)"}
              </label>
              <input
                type="number"
                value={deltaT}
                onChange={(e) => setDeltaT(e.target.value)}
                step={1}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}

          {sensibleMode === "heat_and_airflow" && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Q (BTU/hr)" : "Q (W)"}
                </label>
                <input
                  type="number"
                  value={qSensible}
                  onChange={(e) => setQSensible(e.target.value)}
                  step={100}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Airflow (CFM)" : "Airflow (m³/s)"}
                </label>
                <input
                  type="number"
                  value={airflowCfm}
                  onChange={(e) => setAirflowCfm(e.target.value)}
                  step={isIP ? 10 : 0.01}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* --- Cooling & dehumidification parameters --- */}
      {processType === "cooling_dehumidification" && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Mode</label>
            <select
              value={coolingMode}
              onChange={(e) => setCoolingMode(e.target.value as CoolingDehumMode)}
              className={selectClass}
            >
              {COOLING_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {coolingMode === "forward" && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "ADP Tdb (°F)" : "ADP Tdb (°C)"}
                </label>
                <input
                  type="number"
                  value={adpTdb}
                  onChange={(e) => setAdpTdb(e.target.value)}
                  step={1}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">BF (0–1)</label>
                <input
                  type="number"
                  value={bypassFactor}
                  onChange={(e) => setBypassFactor(e.target.value)}
                  min={0}
                  max={1}
                  step={0.01}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
            </div>
          )}

          {coolingMode === "reverse" && (
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-xs text-text-muted mb-1">
                  {isIP ? "Leaving Tdb (°F)" : "Leaving Tdb (°C)"}
                </label>
                <input
                  type="number"
                  value={leavingTdb}
                  onChange={(e) => setLeavingTdb(e.target.value)}
                  step={1}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted mb-1">Leaving RH (%)</label>
                <input
                  type="number"
                  value={leavingRH}
                  onChange={(e) => setLeavingRH(e.target.value)}
                  step={1}
                  placeholder="—"
                  className={inputClass}
                />
              </div>
            </div>
          )}
        </>
      )}

      {/* --- Adiabatic mixing parameters --- */}
      {processType === "adiabatic_mixing" && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Stream 2</label>
            <select
              value={stream2PairIndex}
              onChange={(e) => {
                setStream2PairIndex(parseInt(e.target.value));
                setStream2Val1("");
                setStream2Val2("");
                setError(null);
              }}
              className={selectClass}
            >
              {INPUT_PAIRS.map((p, i) => (
                <option key={i} value={i}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {(() => {
              const s2Pair = INPUT_PAIRS[stream2PairIndex].value;
              const [s2Label1, s2Label2] = getFieldLabels(s2Pair, unitSystem);
              return (
                <>
                  <div>
                    <label className="block text-xs text-text-muted mb-1">{s2Label1}</label>
                    <input
                      type="number"
                      value={stream2Val1}
                      onChange={(e) => setStream2Val1(e.target.value)}
                      step={getFieldStep(s2Pair[0])}
                      placeholder="—"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-text-muted mb-1">{s2Label2}</label>
                    <input
                      type="number"
                      value={stream2Val2}
                      onChange={(e) => setStream2Val2(e.target.value)}
                      step={getFieldStep(s2Pair[1])}
                      placeholder="—"
                      className={inputClass}
                    />
                  </div>
                </>
              );
            })()}
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Stream 1 Fraction (0–1)</label>
            <input
              type="number"
              value={mixingFraction}
              onChange={(e) => setMixingFraction(e.target.value)}
              min={0}
              max={1}
              step={0.01}
              placeholder="—"
              className={inputClass}
            />
          </div>
        </>
      )}

      {/* --- Steam humidification parameters --- */}
      {processType === "steam_humidification" && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Mode</label>
            <select
              value={humidMode}
              onChange={(e) => setHumidMode(e.target.value as HumidificationMode)}
              className={selectClass}
            >
              {STEAM_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {humidMode === "target_rh" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">Target RH (%)</label>
              <input
                type="number"
                value={targetRH}
                onChange={(e) => setTargetRH(e.target.value)}
                min={0}
                max={100}
                step={1}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}

          {humidMode === "target_w" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">
                {isIP ? "Target W (lb/lb)" : "Target W (kg/kg)"}
              </label>
              <input
                type="number"
                value={targetW}
                onChange={(e) => setTargetW(e.target.value)}
                step={0.0001}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}
        </>
      )}

      {/* --- Adiabatic humidification parameters --- */}
      {processType === "adiabatic_humidification" && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Mode</label>
            <select
              value={humidMode}
              onChange={(e) => setHumidMode(e.target.value as HumidificationMode)}
              className={selectClass}
            >
              {ADIABATIC_HUMID_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {humidMode === "effectiveness" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">Effectiveness (0–1)</label>
              <input
                type="number"
                value={effectiveness}
                onChange={(e) => setEffectiveness(e.target.value)}
                min={0}
                max={1}
                step={0.01}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}

          {humidMode === "target_rh" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">Target RH (%)</label>
              <input
                type="number"
                value={targetRH}
                onChange={(e) => setTargetRH(e.target.value)}
                min={0}
                max={100}
                step={1}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}
        </>
      )}

      {/* --- Heated water spray parameters --- */}
      {processType === "heated_water_humidification" && (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">
              {isIP ? "Water Temp (°F)" : "Water Temp (°C)"}
            </label>
            <input
              type="number"
              value={waterTemperature}
              onChange={(e) => setWaterTemperature(e.target.value)}
              step={1}
              placeholder="—"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">Effectiveness (0–1)</label>
            <input
              type="number"
              value={effectiveness}
              onChange={(e) => setEffectiveness(e.target.value)}
              min={0}
              max={1}
              step={0.01}
              placeholder="—"
              className={inputClass}
            />
          </div>
        </div>
      )}

      {/* --- Direct evaporative parameters --- */}
      {processType === "direct_evaporative" && (
        <div>
          <label className="block text-xs text-text-muted mb-1">Effectiveness (0–1)</label>
          <input
            type="number"
            value={effectiveness}
            onChange={(e) => setEffectiveness(e.target.value)}
            min={0}
            max={1}
            step={0.01}
            placeholder="—"
            className={inputClass}
          />
        </div>
      )}

      {/* --- Indirect evaporative parameters --- */}
      {processType === "indirect_evaporative" && (
        <div>
          <label className="block text-xs text-text-muted mb-1">Effectiveness (0–1)</label>
          <input
            type="number"
            value={effectiveness}
            onChange={(e) => setEffectiveness(e.target.value)}
            min={0}
            max={1}
            step={0.01}
            placeholder="—"
            className={inputClass}
          />
        </div>
      )}

      {/* --- Indirect-Direct two-stage parameters --- */}
      {processType === "indirect_direct_evaporative" && (
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs text-text-muted mb-1">IEC Eff. (0–1)</label>
            <input
              type="number"
              value={iecEffectiveness}
              onChange={(e) => setIecEffectiveness(e.target.value)}
              min={0}
              max={1}
              step={0.01}
              placeholder="—"
              className={inputClass}
            />
          </div>
          <div>
            <label className="block text-xs text-text-muted mb-1">DEC Eff. (0–1)</label>
            <input
              type="number"
              value={decEffectiveness}
              onChange={(e) => setDecEffectiveness(e.target.value)}
              min={0}
              max={1}
              step={0.01}
              placeholder="—"
              className={inputClass}
            />
          </div>
        </div>
      )}

      {/* --- Chemical dehumidification parameters --- */}
      {processType === "chemical_dehumidification" && (
        <>
          <div>
            <label className="block text-xs text-text-muted mb-1">Mode</label>
            <select
              value={dehumMode}
              onChange={(e) => setDehumMode(e.target.value as DehumidificationMode)}
              className={selectClass}
            >
              {CHEM_DEHUM_MODES.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {dehumMode === "target_w" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">
                {isIP ? "Target W (lb/lb)" : "Target W (kg/kg)"}
              </label>
              <input
                type="number"
                value={targetW}
                onChange={(e) => setTargetW(e.target.value)}
                step={0.0001}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}

          {dehumMode === "target_rh" && (
            <div>
              <label className="block text-xs text-text-muted mb-1">Target RH (%)</label>
              <input
                type="number"
                value={targetRH}
                onChange={(e) => setTargetRH(e.target.value)}
                min={0}
                max={100}
                step={1}
                placeholder="—"
                className={inputClass}
              />
            </div>
          )}
        </>
      )}

      {/* Error */}
      {error && (
        <div className="text-xs text-red-400 bg-red-400/10 rounded px-2 py-1.5">
          {error}
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={loading || !startVal1 || !startVal2}
        className="w-full py-1.5 bg-accent hover:bg-accent-hover text-white text-sm font-medium
                   rounded transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
      >
        {loading ? "Calculating..." : "Add Process"}
      </button>
    </form>
  );
}
