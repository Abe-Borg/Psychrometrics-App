import { useState } from "react";
import { useStore } from "../../store/useStore";
import { fmt } from "../../utils/formatting";
import type { StatePointOutput } from "../../types/psychro";

const POINT_COLORS = [
  "#ff6b6b", "#5bf5a9", "#f5c45b", "#5b9cf5",
  "#c45bf5", "#ff9f43", "#54a0ff", "#ff6348",
];

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-0.5">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary font-mono text-xs">{value}</span>
    </div>
  );
}

function StatePointCard({
  sp,
  index,
  onRemove,
}: {
  sp: StatePointOutput;
  index: number;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const color = POINT_COLORS[index % POINT_COLORS.length];
  const isIP = sp.unit_system === "IP";

  return (
    <div className="border border-border rounded bg-bg-primary">
      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-bg-tertiary/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className="text-sm text-text-primary font-medium flex-1 truncate">
          {sp.label || `Point ${index + 1}`}
        </span>
        <span className="text-xs text-text-muted font-mono">
          {fmt(sp.Tdb, 1)}° / {fmt(sp.RH, 0)}%
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="text-text-muted hover:text-red-400 transition-colors text-xs px-1 cursor-pointer"
          title="Remove point"
        >
          ✕
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-3 pb-2 border-t border-border text-xs">
          <div className="pt-2 space-y-0">
            <PropertyRow label={isIP ? "Dry-Bulb" : "Dry-Bulb"} value={`${fmt(sp.Tdb, 2)} ${isIP ? "°F" : "°C"}`} />
            <PropertyRow label="Wet-Bulb" value={`${fmt(sp.Twb, 2)} ${isIP ? "°F" : "°C"}`} />
            <PropertyRow label="Dew Point" value={`${fmt(sp.Tdp, 2)} ${isIP ? "°F" : "°C"}`} />
            <PropertyRow label="RH" value={`${fmt(sp.RH, 2)}%`} />
            <PropertyRow label="Humidity Ratio" value={`${fmt(sp.W_display, 2)} ${isIP ? "gr/lb" : "g/kg"}`} />
            <PropertyRow label="W" value={`${sp.W.toFixed(7)} ${isIP ? "lb/lb" : "kg/kg"}`} />
            <PropertyRow label="Enthalpy" value={`${fmt(sp.h, 2)} ${isIP ? "BTU/lb" : "kJ/kg"}`} />
            <PropertyRow label="Sp. Volume" value={`${fmt(sp.v, 4)} ${isIP ? "ft³/lb" : "m³/kg"}`} />
            <PropertyRow label="Vapor Press." value={`${sp.Pv.toFixed(4)} ${isIP ? "psi" : "Pa"}`} />
            <PropertyRow label="Sat. Press." value={`${sp.Ps.toFixed(4)} ${isIP ? "psi" : "Pa"}`} />
            <PropertyRow label="Deg. of Sat." value={`${fmt(sp.mu * 100, 2)}%`} />
          </div>
          <div className="mt-2 pt-2 border-t border-border text-text-muted">
            Input: {sp.input_pair[0]}={sp.input_values[0]}, {sp.input_pair[1]}={sp.input_values[1]}
          </div>
        </div>
      )}
    </div>
  );
}

export default function StatePointList() {
  const { statePoints, removeStatePoint, clearStatePoints } = useStore();

  if (statePoints.length === 0) {
    return (
      <p className="text-xs text-text-muted italic">
        No points defined. Add one above.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {statePoints.map((sp, i) => (
        <StatePointCard
          key={`${sp.label}-${i}`}
          sp={sp}
          index={i}
          onRemove={() => removeStatePoint(i)}
        />
      ))}

      {statePoints.length > 1 && (
        <button
          onClick={clearStatePoints}
          className="text-xs text-text-muted hover:text-red-400 transition-colors
                     self-end mt-1 cursor-pointer"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
