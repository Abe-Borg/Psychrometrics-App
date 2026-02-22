import { useState } from "react";
import { useStore } from "../../store/useStore";
import type { ChartVisibility } from "../../store/useStore";

const LEGEND_ITEMS: { key: keyof ChartVisibility; label: string; color: string }[] = [
  { key: "rhLines", label: "RH Lines", color: "#5b9cf5" },
  { key: "twbLines", label: "Wet-Bulb Lines", color: "#5bf5a9" },
  { key: "enthalpyLines", label: "Enthalpy Lines", color: "#f5c45b" },
  { key: "volumeLines", label: "Volume Lines", color: "#c45bf5" },
  { key: "statePoints", label: "State Points", color: "#ff6b6b" },
  { key: "processes", label: "Processes", color: "#ff9f43" },
  { key: "coil", label: "Coil Path", color: "#00d2d3" },
  { key: "shrLines", label: "SHR Lines", color: "#ff4757" },
];

export default function ChartLegend() {
  const { visibility, toggleVisibility } = useStore();
  const [collapsed, setCollapsed] = useState(true);

  return (
    <div className="absolute top-2 left-2 z-40">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="px-2 py-1 text-xs bg-bg-secondary/90 border border-border rounded
                   text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
      >
        {collapsed ? "Layers \u25B6" : "Layers \u25BC"}
      </button>

      {!collapsed && (
        <div className="mt-1 bg-bg-secondary/95 border border-border rounded p-2 shadow-lg min-w-[160px]">
          {LEGEND_ITEMS.map(({ key, label, color }) => (
            <label
              key={key}
              className="flex items-center gap-2 py-0.5 text-xs text-text-secondary hover:text-text-primary cursor-pointer"
            >
              <input
                type="checkbox"
                checked={visibility[key]}
                onChange={() => toggleVisibility(key)}
                className="accent-accent"
              />
              <span
                className="w-3 h-0.5 inline-block rounded"
                style={{ backgroundColor: color }}
              />
              {label}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
