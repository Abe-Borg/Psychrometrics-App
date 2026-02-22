import { useEffect, useMemo, useState, useCallback } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout, Config, PlotHoverEvent } from "plotly.js";
import { useStore } from "../../store/useStore";
import { getChartData } from "../../api/client";
import { fmt } from "../../utils/formatting";
import { calcPropertiesAtCursor, type HoverProperties } from "../../utils/hoverCalc";

// Chart line colors — reference our CSS custom properties conceptually
const COLORS = {
  saturation: "#f5725b",
  rh: "#5b9cf5",
  twb: "#5bf5a9",
  enthalpy: "#f5c45b",
  volume: "#c45bf5",
  statePoint: "#ff6b6b",
  grid: "#2e3348",
  bg: "#0f1117",
  paper: "#0f1117",
  text: "#9399b2",
  textBright: "#e8eaf0",
};

// Marker colors for state points — cycle through these
const POINT_COLORS = [
  "#ff6b6b", "#5bf5a9", "#f5c45b", "#5b9cf5",
  "#c45bf5", "#ff9f43", "#54a0ff", "#ff6348",
];

// Process line colors by type
const PROCESS_COLORS: Record<string, string> = {
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

const PROCESS_LABELS: Record<string, string> = {
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

export default function PsychroChart() {
  const {
    chartData, chartLoading, chartError,
    unitSystem, pressure,
    setChartData, setChartLoading, setChartError,
    statePoints,
    processes,
  } = useStore();

  // Hover tooltip state
  const [hoverProps, setHoverProps] = useState<HoverProperties | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);

  const handleHover = useCallback(
    (event: Readonly<PlotHoverEvent>) => {
      const point = event.points?.[0];
      if (!point) return;
      const Tdb = point.x as number;
      const W_display = point.y as number;
      const props = calcPropertiesAtCursor(Tdb, W_display, pressure, unitSystem);
      setHoverProps(props);
      // Position tooltip near cursor using the event's bounding box
      if (event.event) {
        const evt = event.event as MouseEvent;
        setHoverPos({ x: evt.offsetX, y: evt.offsetY });
      }
    },
    [pressure, unitSystem]
  );

  const handleUnhover = useCallback(() => {
    setHoverProps(null);
    setHoverPos(null);
  }, []);

  // Fetch chart data when unit system or pressure changes
  useEffect(() => {
    let cancelled = false;
    async function load() {
      setChartLoading(true);
      try {
        const data = await getChartData(unitSystem, pressure);
        if (!cancelled) setChartData(data);
      } catch (e) {
        if (!cancelled) setChartError(e instanceof Error ? e.message : "Failed to load chart data");
      } finally {
        if (!cancelled) setChartLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [unitSystem, pressure]);

  // Build Plotly traces from chart data
  const traces = useMemo<Data[]>(() => {
    if (!chartData) return [];

    const t: Data[] = [];

    // --- Constant volume lines (draw first, behind everything) ---
    Object.entries(chartData.volume_lines).forEach(([label, points], i) => {
      t.push({
        x: points.map((p) => p.Tdb),
        y: points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color: COLORS.volume, width: 0.7, dash: "dot" },
        name: `v=${label}`,
        legendgroup: "volume",
        showlegend: i === 0,
        hoverinfo: "skip",
      });
    });

    // --- Constant enthalpy lines ---
    Object.entries(chartData.enthalpy_lines).forEach(([label, points], i) => {
      t.push({
        x: points.map((p) => p.Tdb),
        y: points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color: COLORS.enthalpy, width: 0.7, dash: "dashdot" },
        name: `h=${label}`,
        legendgroup: "enthalpy",
        showlegend: i === 0,
        hoverinfo: "skip",
      });
    });

    // --- Constant wet-bulb lines ---
    Object.entries(chartData.twb_lines).forEach(([label, points], i) => {
      t.push({
        x: points.map((p) => p.Tdb),
        y: points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color: COLORS.twb, width: 0.8, dash: "dash" },
        name: `Twb=${label}°`,
        legendgroup: "twb",
        showlegend: i === 0,
        hoverinfo: "skip",
      });
    });

    // --- Constant RH lines ---
    Object.entries(chartData.rh_lines).forEach(([label, points], i) => {
      t.push({
        x: points.map((p) => p.Tdb),
        y: points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color: COLORS.rh, width: 0.9, dash: "solid" },
        opacity: 0.5,
        name: `${label}% RH`,
        legendgroup: "rh",
        showlegend: i === 0,
        hoverinfo: "skip",
      });
    });

    // --- Saturation curve (100% RH) — on top ---
    t.push({
      x: chartData.saturation_curve.map((p) => p.Tdb),
      y: chartData.saturation_curve.map((p) => p.W_display),
      mode: "lines",
      type: "scatter",
      line: { color: COLORS.saturation, width: 2.5 },
      name: "Saturation (100% RH)",
      legendgroup: "saturation",
      hoverinfo: "skip",
    });

    // --- Hover mesh: invisible dense grid for cursor property detection ---
    // We use the RH lines as hover targets since they cover the valid chart area
    const hoverX: number[] = [];
    const hoverY: number[] = [];
    // Sample points from every RH line plus the saturation curve
    const allHoverSources = [
      ...Object.values(chartData.rh_lines),
      chartData.saturation_curve,
    ];
    for (const line of allHoverSources) {
      for (let i = 0; i < line.length; i += 3) {
        hoverX.push(line[i].Tdb);
        hoverY.push(line[i].W_display);
      }
    }
    t.push({
      x: hoverX,
      y: hoverY,
      mode: "markers",
      type: "scatter",
      marker: { size: 1, color: "rgba(0,0,0,0)" },
      showlegend: false,
      hoverinfo: "none",
    });

    // --- State points ---
    statePoints.forEach((sp, i) => {
      const color = POINT_COLORS[i % POINT_COLORS.length];
      const wUnit = sp.unit_system === "IP" ? "gr/lb" : "g/kg";
      const tUnit = sp.unit_system === "IP" ? "°F" : "°C";

      t.push({
        x: [sp.Tdb],
        y: [sp.W_display],
        mode: "text+markers" as const,
        type: "scatter" as const,
        marker: {
          color,
          size: 12,
          symbol: "circle",
          line: { color: "#fff", width: 1.5 },
        },
        text: [sp.label || `P${i + 1}`],
        textposition: "top center",
        textfont: { color: COLORS.textBright, size: 12, family: "IBM Plex Sans" },
        name: sp.label || `Point ${i + 1}`,
        legendgroup: `sp-${i}`,
        hovertemplate:
          `<b>${sp.label || `Point ${i + 1}`}</b><br>` +
          `Tdb: ${fmt(sp.Tdb, 1)}${tUnit}<br>` +
          `Twb: ${fmt(sp.Twb, 1)}${tUnit}<br>` +
          `Tdp: ${fmt(sp.Tdp, 1)}${tUnit}<br>` +
          `RH: ${fmt(sp.RH, 1)}%<br>` +
          `W: ${fmt(sp.W_display, 1)} ${wUnit}<br>` +
          `h: ${fmt(sp.h, 2)} ${sp.unit_system === "IP" ? "BTU/lb" : "kJ/kg"}<br>` +
          `v: ${fmt(sp.v, 2)} ${sp.unit_system === "IP" ? "ft³/lb" : "m³/kg"}` +
          `<extra></extra>`,
      });
    });

    // --- Process lines ---
    processes.forEach((proc, i) => {
      const color = PROCESS_COLORS[proc.process_type] ?? "#aaa";
      const procLabel = `Process ${i + 1}: ${PROCESS_LABELS[proc.process_type] ?? proc.process_type}`;
      const procIsIP = proc.unit_system === "IP";
      const procTUnit = procIsIP ? "°F" : "°C";
      const procWUnit = procIsIP ? "gr/lb" : "g/kg";

      // Path line
      t.push({
        x: proc.path_points.map((p) => p.Tdb),
        y: proc.path_points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color, width: 2.5, dash: "solid" },
        name: procLabel,
        legendgroup: `proc-${i}`,
        showlegend: true,
        hoverinfo: "skip",
      });

      // Start point marker
      const sp = proc.start_point;
      t.push({
        x: [sp.Tdb],
        y: [sp.W_display],
        mode: "markers",
        type: "scatter",
        marker: {
          color,
          size: 9,
          symbol: "circle",
          line: { color: "#fff", width: 1 },
        },
        name: `${procLabel} start`,
        legendgroup: `proc-${i}`,
        showlegend: false,
        hovertemplate:
          `<b>${procLabel} - Start</b><br>` +
          `Tdb: ${fmt(sp.Tdb, 1)}${procTUnit}<br>` +
          `RH: ${fmt(sp.RH, 1)}%<br>` +
          `W: ${fmt(sp.W_display, 1)} ${procWUnit}` +
          `<extra></extra>`,
      });

      // End point marker
      const ep = proc.end_point;
      t.push({
        x: [ep.Tdb],
        y: [ep.W_display],
        mode: "markers",
        type: "scatter",
        marker: {
          color,
          size: 9,
          symbol: "diamond",
          line: { color: "#fff", width: 1 },
        },
        name: `${procLabel} end`,
        legendgroup: `proc-${i}`,
        showlegend: false,
        hovertemplate:
          `<b>${procLabel} - End</b><br>` +
          `Tdb: ${fmt(ep.Tdb, 1)}${procTUnit}<br>` +
          `RH: ${fmt(ep.RH, 1)}%<br>` +
          `W: ${fmt(ep.W_display, 1)} ${procWUnit}` +
          `<extra></extra>`,
      });
    });

    return t;
  }, [chartData, statePoints, processes]);

  // Layout
  const layout = useMemo<Partial<Layout>>(() => {
    const ranges = chartData?.ranges;
    const isIP = unitSystem === "IP";

    // Process direction arrows
    const annotations = processes.map((proc) => {
      const pts = proc.path_points;
      const color = PROCESS_COLORS[proc.process_type] ?? "#aaa";
      const fromIdx = Math.floor(pts.length * 0.4);
      const toIdx = Math.floor(pts.length * 0.6);
      const from = pts[fromIdx];
      const to = pts[toIdx];
      return {
        x: to.Tdb,
        y: to.W_display,
        ax: from.Tdb,
        ay: from.W_display,
        xref: "x" as const,
        yref: "y" as const,
        axref: "x" as const,
        ayref: "y" as const,
        showarrow: true,
        arrowhead: 3,
        arrowsize: 1.5,
        arrowwidth: 2,
        arrowcolor: color,
        opacity: 0.8,
        text: "",
      };
    });

    return {
      autosize: true,
      margin: { l: 65, r: 30, t: 40, b: 55 },
      paper_bgcolor: COLORS.paper,
      plot_bgcolor: COLORS.bg,
      font: { family: "IBM Plex Sans, system-ui, sans-serif", color: COLORS.text },
      title: {
        text: `Psychrometric Chart (${isIP ? "IP" : "SI"})`,
        font: { size: 15, color: COLORS.textBright },
        x: 0.02,
        xanchor: "left",
      },
      xaxis: {
        title: { text: isIP ? "Dry-Bulb Temperature (°F)" : "Dry-Bulb Temperature (°C)" },
        range: ranges ? [ranges.Tdb_min, ranges.Tdb_max] : undefined,
        gridcolor: COLORS.grid,
        gridwidth: 1,
        zeroline: false,
        dtick: isIP ? 5 : 5,
        tickfont: { size: 11 },
      },
      yaxis: {
        title: { text: isIP ? "Humidity Ratio (grains/lb)" : "Humidity Ratio (g/kg)" },
        range: ranges ? [ranges.W_min, ranges.W_max] : undefined,
        gridcolor: COLORS.grid,
        gridwidth: 1,
        zeroline: false,
        dtick: isIP ? 10 : 2,
        tickfont: { size: 11 },
      },
      legend: {
        x: 1,
        y: 1,
        xanchor: "right",
        bgcolor: "rgba(15,17,23,0.85)",
        bordercolor: COLORS.grid,
        borderwidth: 1,
        font: { size: 11 },
      },
      hovermode: "closest",
      dragmode: "pan",
      annotations,
    };
  }, [chartData, unitSystem, processes]);

  const config: Partial<Config> = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    scrollZoom: true,
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
  };

  if (chartLoading) {
    return (
      <div className="flex items-center justify-center h-full text-text-secondary">
        <div className="text-center">
          <div className="text-lg mb-2">Loading chart data...</div>
          <div className="text-sm text-text-muted">Generating psychrometric lines</div>
        </div>
      </div>
    );
  }

  if (chartError) {
    return (
      <div className="flex items-center justify-center h-full text-red-400">
        <div className="text-center">
          <div className="text-lg mb-2">Error loading chart</div>
          <div className="text-sm">{chartError}</div>
        </div>
      </div>
    );
  }

  const isIP = unitSystem === "IP";
  const tUnit = isIP ? "°F" : "°C";
  const wUnit = isIP ? "gr/lb" : "g/kg";
  const hUnit = isIP ? "BTU/lb" : "kJ/kg";
  const vUnit = isIP ? "ft³/lb" : "m³/kg";

  return (
    <div className="w-full h-full relative">
      <Plot
        data={traces}
        layout={layout}
        config={config}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
        onHover={handleHover}
        onUnhover={handleUnhover}
      />

      {/* Hover tooltip */}
      {hoverProps && hoverPos && (
        <div
          className="absolute pointer-events-none z-50 bg-bg-secondary/95 border border-border
                     rounded px-3 py-2 text-xs font-mono shadow-lg"
          style={{
            left: hoverPos.x + 16,
            top: hoverPos.y - 80,
          }}
        >
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
            <span className="text-text-muted">Tdb</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.Tdb, 1)}{tUnit}</span>
            <span className="text-text-muted">W</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.W_display, 1)} {wUnit}</span>
            <span className="text-text-muted">RH</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.RH, 1)}%</span>
            <span className="text-text-muted">Twb</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.Twb, 1)}{tUnit}</span>
            <span className="text-text-muted">Tdp</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.Tdp, 1)}{tUnit}</span>
            <span className="text-text-muted">h</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.h, 1)} {hUnit}</span>
            <span className="text-text-muted">v</span>
            <span className="text-text-primary text-right">{fmt(hoverProps.v, 2)} {vUnit}</span>
          </div>
        </div>
      )}
    </div>
  );
}
