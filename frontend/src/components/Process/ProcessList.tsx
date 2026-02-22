import { useState } from "react";
import { useStore } from "../../store/useStore";
import { fmt } from "../../utils/formatting";
import type { ProcessOutput, ProcessType } from "../../types/psychro";

const PROCESS_COLORS: Record<ProcessType, string> = {
  sensible_heating: "#ff9f43",
  sensible_cooling: "#ff9f43",
  cooling_dehumidification: "#54e0ff",
  adiabatic_mixing: "#e454ff",
  steam_humidification: "#5bf5a9",
  adiabatic_humidification: "#5bf5a9",
  heated_water_humidification: "#5bf5a9",
  direct_evaporative: "#f5c45b",
  indirect_evaporative: "#f5c45b",
  indirect_direct_evaporative: "#f5c45b",
  chemical_dehumidification: "#c45bf5",
  sensible_reheat: "#ff6348",
};

const PROCESS_LABELS: Record<ProcessType, string> = {
  sensible_heating: "Sensible Heating",
  sensible_cooling: "Sensible Cooling",
  cooling_dehumidification: "Cooling & Dehum",
  adiabatic_mixing: "Adiabatic Mixing",
  steam_humidification: "Steam Humid.",
  adiabatic_humidification: "Adiabatic Humid.",
  heated_water_humidification: "Heated Water",
  direct_evaporative: "Direct Evap.",
  indirect_evaporative: "Indirect Evap.",
  indirect_direct_evaporative: "IDEC (Two-Stage)",
  chemical_dehumidification: "Chem. Dehum.",
  sensible_reheat: "Sensible Reheat",
};

function PropertyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-0.5">
      <span className="text-text-muted">{label}</span>
      <span className="text-text-primary font-mono text-xs">{value}</span>
    </div>
  );
}

function ProcessCard({
  proc,
  onRemove,
}: {
  proc: ProcessOutput;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const color = PROCESS_COLORS[proc.process_type];
  const label = PROCESS_LABELS[proc.process_type];
  const isIP = proc.unit_system === "IP";
  const tUnit = isIP ? "°F" : "°C";
  const wUnit = isIP ? "gr/lb" : "g/kg";
  const hUnit = isIP ? "BTU/lb" : "kJ/kg";
  const m = proc.metadata;

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
          {label}
        </span>
        <span className="text-xs text-text-muted font-mono">
          {fmt(proc.start_point.Tdb, 1)}° → {fmt(proc.end_point.Tdb, 1)}°
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="text-text-muted hover:text-red-400 transition-colors text-xs px-1 cursor-pointer"
          title="Remove process"
        >
          ✕
        </button>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="px-3 pb-2 border-t border-border text-xs">
          <div className="pt-2 space-y-0">
            {/* Start / End summary */}
            <PropertyRow
              label="Start Tdb"
              value={`${fmt(proc.start_point.Tdb, 2)} ${tUnit}`}
            />
            <PropertyRow
              label="End Tdb"
              value={`${fmt(proc.end_point.Tdb, 2)} ${tUnit}`}
            />
            <PropertyRow
              label="Start W"
              value={`${fmt(proc.start_point.W_display, 2)} ${wUnit}`}
            />
            <PropertyRow
              label="End W"
              value={`${fmt(proc.end_point.W_display, 2)} ${wUnit}`}
            />

            {/* Sensible metadata */}
            {(proc.process_type === "sensible_heating" ||
              proc.process_type === "sensible_cooling") && (
              <>
                {m.delta_T != null && (
                  <PropertyRow
                    label="Delta T"
                    value={`${fmt(m.delta_T as number, 2)} ${tUnit}`}
                  />
                )}
                {m.Qs_per_unit_mass != null && (
                  <PropertyRow
                    label="Qs/mass"
                    value={`${fmt(m.Qs_per_unit_mass as number, 2)} ${hUnit}`}
                  />
                )}
                {m.Q_sensible != null && (
                  <PropertyRow
                    label="Q Sensible"
                    value={`${fmt(m.Q_sensible as number, 0)} ${isIP ? "BTU/hr" : "W"}`}
                  />
                )}
                {m.airflow != null && (
                  <PropertyRow
                    label="Airflow"
                    value={`${fmt(m.airflow as number, 1)} ${isIP ? "CFM" : "m³/s"}`}
                  />
                )}
                {m.C_factor != null && (
                  <PropertyRow
                    label="C Factor"
                    value={fmt(m.C_factor as number, 4)}
                  />
                )}
              </>
            )}

            {/* Cooling & dehum metadata */}
            {proc.process_type === "cooling_dehumidification" && (
              <>
                {m.ADP_Tdb != null && (
                  <PropertyRow
                    label="ADP Tdb"
                    value={`${fmt(m.ADP_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.ADP_W_display != null && (
                  <PropertyRow
                    label="ADP W"
                    value={`${fmt(m.ADP_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.BF != null && (
                  <PropertyRow label="BF" value={fmt(m.BF as number, 4)} />
                )}
                {m.CF != null && (
                  <PropertyRow label="CF" value={fmt(m.CF as number, 4)} />
                )}
                {m.Qs != null && (
                  <PropertyRow
                    label="Qs"
                    value={`${fmt(m.Qs as number, 2)} ${hUnit}`}
                  />
                )}
                {m.Ql != null && (
                  <PropertyRow
                    label="Ql"
                    value={`${fmt(m.Ql as number, 2)} ${hUnit}`}
                  />
                )}
                {m.Qt != null && (
                  <PropertyRow
                    label="Qt"
                    value={`${fmt(m.Qt as number, 2)} ${hUnit}`}
                  />
                )}
                {m.SHR != null && (
                  <PropertyRow label="SHR" value={fmt(m.SHR as number, 4)} />
                )}
              </>
            )}

            {/* Mixing metadata */}
            {proc.process_type === "adiabatic_mixing" && (
              <>
                {m.mixing_fraction != null && (
                  <PropertyRow
                    label="Stream 1 Fraction"
                    value={fmt(m.mixing_fraction as number, 3)}
                  />
                )}
                {m.Tdb_mix != null && (
                  <PropertyRow
                    label="Mix Tdb"
                    value={`${fmt(m.Tdb_mix as number, 2)} ${tUnit}`}
                  />
                )}
                {m.W_mix_display != null && (
                  <PropertyRow
                    label="Mix W"
                    value={`${fmt(m.W_mix_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.h_mix != null && (
                  <PropertyRow
                    label="Mix h"
                    value={`${fmt(m.h_mix as number, 2)} ${hUnit}`}
                  />
                )}
              </>
            )}

            {/* Steam humidification metadata */}
            {proc.process_type === "steam_humidification" && (
              <>
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.delta_h != null && (
                  <PropertyRow
                    label="Delta h"
                    value={`${fmt(m.delta_h as number, 2)} ${hUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Adiabatic humidification metadata */}
            {proc.process_type === "adiabatic_humidification" && (
              <>
                {m.effectiveness != null && (
                  <PropertyRow label="Effectiveness" value={fmt(m.effectiveness as number, 3)} />
                )}
                {m.Twb != null && (
                  <PropertyRow label="Twb" value={`${fmt(m.Twb as number, 2)} ${tUnit}`} />
                )}
                {m.delta_Tdb != null && (
                  <PropertyRow
                    label="Delta Tdb"
                    value={`${fmt(m.delta_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Heated water humidification metadata */}
            {proc.process_type === "heated_water_humidification" && (
              <>
                {m.effectiveness != null && (
                  <PropertyRow label="Effectiveness" value={fmt(m.effectiveness as number, 3)} />
                )}
                {m.water_temperature != null && (
                  <PropertyRow
                    label="Water Temp"
                    value={`${fmt(m.water_temperature as number, 1)} ${tUnit}`}
                  />
                )}
                {m.delta_Tdb != null && (
                  <PropertyRow
                    label="Delta Tdb"
                    value={`${fmt(m.delta_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.delta_h != null && (
                  <PropertyRow
                    label="Delta h"
                    value={`${fmt(m.delta_h as number, 2)} ${hUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Direct evaporative metadata */}
            {proc.process_type === "direct_evaporative" && (
              <>
                {m.effectiveness != null && (
                  <PropertyRow label="Effectiveness" value={fmt(m.effectiveness as number, 3)} />
                )}
                {m.Twb != null && (
                  <PropertyRow label="Twb" value={`${fmt(m.Twb as number, 2)} ${tUnit}`} />
                )}
                {m.delta_Tdb != null && (
                  <PropertyRow
                    label="Delta Tdb"
                    value={`${fmt(m.delta_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Indirect evaporative metadata */}
            {proc.process_type === "indirect_evaporative" && (
              <>
                {m.effectiveness != null && (
                  <PropertyRow label="Effectiveness" value={fmt(m.effectiveness as number, 3)} />
                )}
                {m.secondary_Twb != null && (
                  <PropertyRow
                    label="Sec. Twb"
                    value={`${fmt(m.secondary_Twb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_Tdb != null && (
                  <PropertyRow
                    label="Delta Tdb"
                    value={`${fmt(m.delta_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Indirect-Direct two-stage metadata */}
            {proc.process_type === "indirect_direct_evaporative" && (
              <>
                {m.iec_effectiveness != null && (
                  <PropertyRow label="IEC Eff." value={fmt(m.iec_effectiveness as number, 3)} />
                )}
                {m.dec_effectiveness != null && (
                  <PropertyRow label="DEC Eff." value={fmt(m.dec_effectiveness as number, 3)} />
                )}
                {m.secondary_Twb != null && (
                  <PropertyRow
                    label="Sec. Twb"
                    value={`${fmt(m.secondary_Twb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.intermediate_Tdb != null && (
                  <PropertyRow
                    label="Mid Tdb"
                    value={`${fmt(m.intermediate_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_Tdb_total != null && (
                  <PropertyRow
                    label="Total Delta Tdb"
                    value={`${fmt(m.delta_Tdb_total as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Chemical dehumidification metadata */}
            {proc.process_type === "chemical_dehumidification" && (
              <>
                {m.h_constant != null && (
                  <PropertyRow
                    label="h (constant)"
                    value={`${fmt(m.h_constant as number, 2)} ${hUnit}`}
                  />
                )}
                {m.delta_Tdb != null && (
                  <PropertyRow
                    label="Delta Tdb"
                    value={`${fmt(m.delta_Tdb as number, 2)} ${tUnit}`}
                  />
                )}
                {m.delta_W_display != null && (
                  <PropertyRow
                    label="Delta W"
                    value={`${fmt(m.delta_W_display as number, 2)} ${wUnit}`}
                  />
                )}
                {m.start_RH != null && (
                  <PropertyRow label="Start RH" value={`${fmt(m.start_RH as number, 1)}%`} />
                )}
                {m.end_RH != null && (
                  <PropertyRow label="End RH" value={`${fmt(m.end_RH as number, 1)}%`} />
                )}
              </>
            )}

            {/* Sensible reheat metadata (same as sensible heating) */}
            {proc.process_type === "sensible_reheat" && (
              <>
                {m.delta_T != null && (
                  <PropertyRow
                    label="Delta T"
                    value={`${fmt(m.delta_T as number, 2)} ${tUnit}`}
                  />
                )}
                {m.Qs_per_unit_mass != null && (
                  <PropertyRow
                    label="Qs/mass"
                    value={`${fmt(m.Qs_per_unit_mass as number, 2)} ${hUnit}`}
                  />
                )}
              </>
            )}
          </div>

          {/* Warnings */}
          {proc.warnings.length > 0 && (
            <div className="mt-2 space-y-1">
              {proc.warnings.map((w, i) => (
                <div
                  key={i}
                  className="text-xs text-yellow-400 bg-yellow-400/10 rounded px-2 py-1.5"
                >
                  {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProcessList() {
  const { processes, removeProcess, clearProcesses } = useStore();

  if (processes.length === 0) {
    return (
      <p className="text-xs text-text-muted italic">
        No processes defined. Add one above.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {processes.map((proc, i) => (
        <ProcessCard
          key={`${proc.process_type}-${i}`}
          proc={proc}
          onRemove={() => removeProcess(i)}
        />
      ))}

      {processes.length > 1 && (
        <button
          onClick={clearProcesses}
          className="text-xs text-text-muted hover:text-red-400 transition-colors
                     self-end mt-1 cursor-pointer"
        >
          Clear all
        </button>
      )}
    </div>
  );
}
