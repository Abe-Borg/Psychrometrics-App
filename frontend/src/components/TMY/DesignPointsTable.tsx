import { useState } from "react";
import type { WeatherDesignPoint, UnitSystem } from "../../types/psychro";
import { fmt } from "../../utils/formatting";

interface Props {
  designPoints: WeatherDesignPoint[];
  unitSystem: UnitSystem;
}

type SortKey = "label" | "point_type" | "dry_bulb" | "wet_bulb" | "dewpoint"
  | "humidity_ratio" | "enthalpy" | "relative_humidity" | "specific_volume" | "time" | "hours_in_cluster";

const COLUMNS: { key: SortKey; label: (us: UnitSystem) => string; width?: string }[] = [
  { key: "label", label: () => "Label" },
  { key: "point_type", label: () => "Type" },
  { key: "dry_bulb", label: (us) => us === "IP" ? "DB (\u00B0F)" : "DB (\u00B0C)" },
  { key: "wet_bulb", label: (us) => us === "IP" ? "WB (\u00B0F)" : "WB (\u00B0C)" },
  { key: "dewpoint", label: (us) => us === "IP" ? "DP (\u00B0F)" : "DP (\u00B0C)" },
  { key: "humidity_ratio", label: (us) => us === "IP" ? "W (gr/lb)" : "W (g/kg)" },
  { key: "enthalpy", label: (us) => us === "IP" ? "h (BTU/lb)" : "h (kJ/kg)" },
  { key: "relative_humidity", label: () => "RH (%)" },
  { key: "specific_volume", label: (us) => us === "IP" ? "v (ft\u00B3/lb)" : "v (m\u00B3/kg)" },
  { key: "time", label: () => "M/D/H" },
  { key: "hours_in_cluster", label: () => "Hrs" },
];

function getSortValue(dp: WeatherDesignPoint, key: SortKey): number | string {
  switch (key) {
    case "label": return dp.label;
    case "point_type": return dp.point_type;
    case "dry_bulb": return dp.dry_bulb;
    case "wet_bulb": return dp.wet_bulb;
    case "dewpoint": return dp.dewpoint;
    case "humidity_ratio": return dp.humidity_ratio;
    case "enthalpy": return dp.enthalpy;
    case "relative_humidity": return dp.relative_humidity;
    case "specific_volume": return dp.specific_volume;
    case "time": return dp.month * 10000 + dp.day * 100 + dp.hour;
    case "hours_in_cluster": return dp.hours_in_cluster ?? 0;
  }
}

export default function DesignPointsTable({ designPoints, unitSystem }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("label");
  const [sortAsc, setSortAsc] = useState(true);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sorted = [...designPoints].sort((a, b) => {
    const va = getSortValue(a, sortKey);
    const vb = getSortValue(b, sortKey);
    const cmp = typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number);
    return sortAsc ? cmp : -cmp;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            {COLUMNS.map((col) => (
              <th
                key={col.key}
                onClick={() => handleSort(col.key)}
                className="px-1.5 py-1 text-left text-text-muted font-medium border-b border-border
                           cursor-pointer hover:text-text-primary select-none whitespace-nowrap"
              >
                {col.label(unitSystem)}
                {sortKey === col.key && (
                  <span className="ml-0.5">{sortAsc ? "\u25B2" : "\u25BC"}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((dp, i) => {
            const isExtreme = dp.point_type === "extreme";
            return (
              <tr
                key={i}
                className={`border-b border-border/50 hover:bg-bg-primary/50 ${
                  isExtreme ? "font-semibold bg-accent/5" : ""
                }`}
              >
                <td className="px-1.5 py-1 whitespace-nowrap">{dp.label}</td>
                <td className="px-1.5 py-1 whitespace-nowrap">
                  <span className={`inline-block px-1 rounded text-[10px] ${
                    isExtreme
                      ? "bg-amber-500/20 text-amber-400"
                      : "bg-blue-500/20 text-blue-400"
                  }`}>
                    {isExtreme ? "extreme" : "cluster"}
                  </span>
                </td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.dry_bulb, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.wet_bulb, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.dewpoint, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.humidity_ratio, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.enthalpy, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.relative_humidity * 100, 1)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums">{fmt(dp.specific_volume, 2)}</td>
                <td className="px-1.5 py-1 text-right tabular-nums whitespace-nowrap">
                  {dp.month}/{dp.day}/{dp.hour}
                </td>
                <td className="px-1.5 py-1 text-right tabular-nums">
                  {dp.hours_in_cluster ?? "\u2014"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
