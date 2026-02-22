import { useState } from "react";
import { useStore } from "../../store/useStore";
import { getPressureFromAltitude } from "../../api/client";

export default function Toolbar() {
  const { unitSystem, pressure, altitude, setUnitSystem, setPressure, setAltitude, clearProcesses } = useStore();
  const [altInput, setAltInput] = useState(altitude.toString());
  const [pressInput, setPressInput] = useState(pressure.toFixed(3));

  async function handleAltitudeSubmit() {
    const alt = parseFloat(altInput);
    if (isNaN(alt)) return;
    try {
      const result = await getPressureFromAltitude(alt, unitSystem);
      setAltitude(alt);
      setPressure(result.pressure);
      setPressInput(result.pressure.toFixed(3));
      clearProcesses();
    } catch (e) {
      console.error("Failed to convert altitude:", e);
    }
  }

  function handlePressureSubmit() {
    const p = parseFloat(pressInput);
    if (isNaN(p) || p <= 0) return;
    setPressure(p);
    clearProcesses();
  }

  function handleUnitToggle() {
    const newUnit = unitSystem === "IP" ? "SI" : "IP";
    const newPressure = newUnit === "IP" ? 14.696 : 101325.0;
    setUnitSystem(newUnit);
    setPressure(newPressure);
    setPressInput(newPressure.toFixed(newUnit === "IP" ? 3 : 0));
    setAltitude(0);
    setAltInput("0");
    clearProcesses();
  }

  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-bg-secondary border-b border-border text-sm">
      {/* App title */}
      <span className="font-semibold text-text-primary tracking-wide mr-2">
        PsychroApp
      </span>

      <div className="w-px h-5 bg-border" />

      {/* Unit system toggle */}
      <button
        onClick={handleUnitToggle}
        className="px-3 py-1 rounded border border-border hover:border-border-hover
                   text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
      >
        {unitSystem === "IP" ? "IP (°F)" : "SI (°C)"}
      </button>

      <div className="w-px h-5 bg-border" />

      {/* Altitude */}
      <div className="flex items-center gap-1.5">
        <label className="text-text-muted">Alt:</label>
        <input
          type="number"
          value={altInput}
          onChange={(e) => setAltInput(e.target.value)}
          onBlur={handleAltitudeSubmit}
          onKeyDown={(e) => e.key === "Enter" && handleAltitudeSubmit()}
          className="w-20 px-2 py-0.5 bg-bg-tertiary border border-border rounded text-text-primary
                     text-center focus:outline-none focus:border-accent"
        />
        <span className="text-text-muted">{unitSystem === "IP" ? "ft" : "m"}</span>
      </div>

      {/* Pressure */}
      <div className="flex items-center gap-1.5">
        <label className="text-text-muted">P:</label>
        <input
          type="number"
          value={pressInput}
          onChange={(e) => setPressInput(e.target.value)}
          onBlur={handlePressureSubmit}
          onKeyDown={(e) => e.key === "Enter" && handlePressureSubmit()}
          step={unitSystem === "IP" ? 0.01 : 100}
          className="w-24 px-2 py-0.5 bg-bg-tertiary border border-border rounded text-text-primary
                     text-center focus:outline-none focus:border-accent"
        />
        <span className="text-text-muted">{unitSystem === "IP" ? "psia" : "Pa"}</span>
      </div>
    </div>
  );
}
