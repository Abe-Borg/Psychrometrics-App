import { useEffect, useMemo } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout, Config } from "plotly.js";
import { useStore } from "../../store/useStore";
import { getChartData } from "../../api/client";
import { fmt } from "../../utils/formatting";

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

export default function PsychroChart() {
  const {
    chartData, chartLoading, chartError,
    unitSystem, pressure,
    setChartData, setChartLoading, setChartError,
    statePoints,
  } = useStore();

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

    return t;
  }, [chartData, statePoints]);

  // Layout
  const layout = useMemo<Partial<Layout>>(() => {
    const ranges = chartData?.ranges;
    const isIP = unitSystem === "IP";

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
    };
  }, [chartData, unitSystem]);

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

  return (
    <div className="w-full h-full">
      <Plot
        data={traces}
        layout={layout}
        config={config}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
      />
    </div>
  );
}
