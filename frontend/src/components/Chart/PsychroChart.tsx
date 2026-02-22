import { useEffect, useMemo, useState, useCallback, useRef } from "react";
import Plot from "react-plotly.js";
import type { Data, Layout, Config, PlotHoverEvent, PlotMouseEvent } from "plotly.js";
import { useStore } from "../../store/useStore";
import { getChartData } from "../../api/client";
import { fmt } from "../../utils/formatting";
import { calcPropertiesAtCursor, type HoverProperties } from "../../utils/hoverCalc";
import ChartLegend from "./ChartLegend";

// Chart line colors — dark theme
const COLORS_DARK = {
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
  legendBg: "rgba(15,17,23,0.85)",
  annotationBg: "rgba(15,17,23,0.8)",
};

// Chart line colors — light theme
const COLORS_LIGHT = {
  saturation: "#d94030",
  rh: "#3a7ae0",
  twb: "#1fad6e",
  enthalpy: "#c99520",
  volume: "#9040d0",
  statePoint: "#e04040",
  grid: "#d4d8e8",
  bg: "#f5f6fa",
  paper: "#f5f6fa",
  text: "#5a6078",
  textBright: "#1a1d27",
  legendBg: "rgba(255,255,255,0.9)",
  annotationBg: "rgba(245,246,250,0.9)",
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

// Coil & SHR overlay colors
const SHR_COLORS = {
  room_shr: "#ff4757",
  gshr: "#ff6b81",
  eshr: "#ff7f50",
  coil: "#00d2d3",
};

export default function PsychroChart() {
  const {
    chartData, chartLoading, chartError,
    unitSystem, pressure,
    setChartData, setChartLoading, setChartError,
    statePoints,
    processes,
    coilResult,
    shrLines,
    gshrResult,
    designDayResult,
    tmyResult,
    tmyDisplayMode,
    setChartRef,
    setPendingClickPoint,
    selectedPointIndex,
    setSelectedPointIndex,
    theme,
    visibility,
  } = useStore();

  const plotRef = useRef<HTMLDivElement>(null);

  // Hover tooltip state
  const [hoverProps, setHoverProps] = useState<HoverProperties | null>(null);
  const [hoverPos, setHoverPos] = useState<{ x: number; y: number } | null>(null);

  // Store chart ref for image export
  useEffect(() => {
    if (plotRef.current) {
      // The actual Plotly div is the first child div with class "js-plotly-plot"
      const plotlyDiv = plotRef.current.querySelector(".js-plotly-plot") as HTMLElement;
      setChartRef(plotlyDiv || plotRef.current);
    }
    return () => setChartRef(null);
  }, [chartData]);

  const COLORS = theme === "light" ? COLORS_LIGHT : COLORS_DARK;

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

  // Click-to-add: extract coordinates from chart click
  const handleClick = useCallback(
    (event: Readonly<PlotMouseEvent>) => {
      const point = event.points?.[0];
      if (!point) return;

      // Check if clicking on a state point marker (customdata or curveNumber detection)
      // State point traces have a specific name pattern; check the trace name
      const traceName = (point.data as { name?: string }).name ?? "";

      // Identify if this is a state point click — state points use "Point N" or custom labels
      const spTraceIndex = statePoints.findIndex((sp, i) =>
        traceName === (sp.label || `Point ${i + 1}`)
      );

      if (spTraceIndex >= 0) {
        // Click on existing state point: select it
        setSelectedPointIndex(spTraceIndex === selectedPointIndex ? null : spTraceIndex);
        return;
      }

      // Click on empty chart area: set pending click point for auto-fill
      const Tdb = point.x as number;
      const W_display = point.y as number;
      setPendingClickPoint({ Tdb, W_display });
    },
    [statePoints, selectedPointIndex, setPendingClickPoint, setSelectedPointIndex]
  );

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
    if (visibility.volumeLines) {
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
    }

    // --- Constant enthalpy lines ---
    if (visibility.enthalpyLines) {
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
    }

    // --- Constant wet-bulb lines ---
    if (visibility.twbLines) {
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
    }

    // --- Constant RH lines ---
    if (visibility.rhLines) {
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
    }

    // --- Saturation curve (100% RH) — always visible ---
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
    const hoverX: number[] = [];
    const hoverY: number[] = [];
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

    // --- TMY data overlay (drawn behind state points) ---
    if (visibility.tmyData && tmyResult && tmyResult.scatter_points.length > 0) {
      if (tmyDisplayMode === "scatter") {
        t.push({
          x: tmyResult.scatter_points.map(p => p.Tdb),
          y: tmyResult.scatter_points.map(p => p.W_display),
          mode: "markers",
          type: "scatter",
          marker: {
            color: tmyResult.scatter_points.map(p => p.month),
            colorscale: "Portland",
            cmin: 1,
            cmax: 12,
            size: 3,
            opacity: 0.15,
          },
          name: `TMY: ${tmyResult.location_name ?? "Data"}`,
          legendgroup: "tmy",
          showlegend: true,
          hoverinfo: "skip",
        });
      } else {
        // Heatmap mode — use bin_matrix
        const matrix = tmyResult.bin_matrix;
        const tdbEdges = tmyResult.bin_Tdb_edges;
        const wEdges = tmyResult.bin_W_edges;

        // Compute bin centers
        const tdbCenters = tdbEdges.slice(0, -1).map((e, i) => (e + tdbEdges[i + 1]) / 2);
        const wCenters = wEdges.slice(0, -1).map((e, i) => (e + wEdges[i + 1]) / 2);

        // Replace 0 with null for transparent bins
        const zData = matrix.map(row => row.map(v => v === 0 ? null : v));

        t.push({
          x: tdbCenters,
          y: wCenters,
          z: zData,
          type: "heatmap",
          colorscale: "YlOrRd",
          showscale: true,
          opacity: 0.6,
          name: `TMY: ${tmyResult.location_name ?? "Heatmap"}`,
          legendgroup: "tmy",
          showlegend: true,
          hovertemplate: "Tdb: %{x:.1f}<br>W: %{y:.1f}<br>Hours: %{z}<extra></extra>",
          colorbar: {
            title: { text: "Hours", side: "right" },
            thickness: 12,
            len: 0.4,
            y: 0.3,
          },
        } as unknown as Data);
      }
    }

    // --- State points ---
    if (visibility.statePoints) {
      statePoints.forEach((sp, i) => {
        const color = POINT_COLORS[i % POINT_COLORS.length];
        const wUnit = sp.unit_system === "IP" ? "gr/lb" : "g/kg";
        const tUnit = sp.unit_system === "IP" ? "°F" : "°C";
        const isSelected = selectedPointIndex === i;

        t.push({
          x: [sp.Tdb],
          y: [sp.W_display],
          mode: "text+markers" as const,
          type: "scatter" as const,
          marker: {
            color,
            size: isSelected ? 16 : 12,
            symbol: "circle",
            line: { color: isSelected ? "#fff" : "#fff", width: isSelected ? 3 : 1.5 },
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
    }

    // --- Process lines ---
    if (visibility.processes) {
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
    }

    // --- Coil analysis path ---
    if (visibility.coil && coilResult) {
      const coilIsIP = coilResult.unit_system === "IP";
      const cTUnit = coilIsIP ? "°F" : "°C";
      const cWUnit = coilIsIP ? "gr/lb" : "g/kg";

      t.push({
        x: coilResult.path_points.map((p) => p.Tdb),
        y: coilResult.path_points.map((p) => p.W_display),
        mode: "lines",
        type: "scatter",
        line: { color: SHR_COLORS.coil, width: 2.5, dash: "solid" },
        name: "Coil Path",
        legendgroup: "coil",
        showlegend: true,
        hoverinfo: "skip",
      });

      const ce = coilResult.entering;
      t.push({
        x: [ce.Tdb],
        y: [ce.W_display],
        mode: "markers",
        type: "scatter",
        marker: { color: SHR_COLORS.coil, size: 10, symbol: "circle", line: { color: "#fff", width: 1.5 } },
        name: "Coil Entering",
        legendgroup: "coil",
        showlegend: false,
        hovertemplate:
          `<b>Coil Entering</b><br>Tdb: ${fmt(ce.Tdb, 1)}${cTUnit}<br>` +
          `RH: ${fmt(ce.RH, 1)}%<br>W: ${fmt(ce.W_display, 1)} ${cWUnit}<extra></extra>`,
      });

      const cl = coilResult.leaving;
      t.push({
        x: [cl.Tdb],
        y: [cl.W_display],
        mode: "markers",
        type: "scatter",
        marker: { color: SHR_COLORS.coil, size: 10, symbol: "diamond", line: { color: "#fff", width: 1.5 } },
        name: "Coil Leaving",
        legendgroup: "coil",
        showlegend: false,
        hovertemplate:
          `<b>Coil Leaving</b><br>Tdb: ${fmt(cl.Tdb, 1)}${cTUnit}<br>` +
          `RH: ${fmt(cl.RH, 1)}%<br>W: ${fmt(cl.W_display, 1)} ${cWUnit}<extra></extra>`,
      });

      const ca = coilResult.adp;
      t.push({
        x: [ca.Tdb],
        y: [ca.W_display],
        mode: "markers",
        type: "scatter",
        marker: { color: SHR_COLORS.coil, size: 12, symbol: "star", line: { color: "#fff", width: 1 } },
        name: "Coil ADP",
        legendgroup: "coil",
        showlegend: false,
        hovertemplate:
          `<b>Coil ADP</b><br>Tdb: ${fmt(ca.Tdb, 1)}${cTUnit}<br>` +
          `RH: ${fmt(ca.RH, 1)}%<br>W: ${fmt(ca.W_display, 1)} ${cWUnit}<extra></extra>`,
      });
    }

    // --- SHR lines ---
    if (visibility.shrLines) {
      shrLines.forEach((shr, i) => {
        const shrIsIP = shr.room_point.unit_system === "IP";
        const sTUnit = shrIsIP ? "°F" : "°C";
        const sWUnit = shrIsIP ? "gr/lb" : "g/kg";
        const shrLabel = `SHR ${shr.shr.toFixed(2)}`;

        t.push({
          x: shr.line_points.map((p) => p.Tdb),
          y: shr.line_points.map((p) => p.W_display),
          mode: "lines",
          type: "scatter",
          line: { color: SHR_COLORS.room_shr, width: 2, dash: "dash" },
          name: shrLabel,
          legendgroup: `shr-${i}`,
          showlegend: true,
          hoverinfo: "skip",
        });

        const sa = shr.adp;
        t.push({
          x: [sa.Tdb],
          y: [sa.W_display],
          mode: "markers",
          type: "scatter",
          marker: { color: SHR_COLORS.room_shr, size: 10, symbol: "star", line: { color: "#fff", width: 1 } },
          name: `${shrLabel} ADP`,
          legendgroup: `shr-${i}`,
          showlegend: false,
          hovertemplate:
            `<b>${shrLabel} ADP</b><br>Tdb: ${fmt(sa.Tdb, 1)}${sTUnit}<br>` +
            `RH: ${fmt(sa.RH, 1)}%<br>W: ${fmt(sa.W_display, 1)} ${sWUnit}<extra></extra>`,
        });
      });

      // --- GSHR / ESHR lines ---
      if (gshrResult) {
        const gIsIP = gshrResult.room_point.unit_system === "IP";
        const gTUnit = gIsIP ? "°F" : "°C";
        const gWUnit = gIsIP ? "gr/lb" : "g/kg";

        t.push({
          x: gshrResult.room_shr_line.map((p) => p.Tdb),
          y: gshrResult.room_shr_line.map((p) => p.W_display),
          mode: "lines",
          type: "scatter",
          line: { color: SHR_COLORS.room_shr, width: 2, dash: "dash" },
          name: `Room SHR ${gshrResult.room_shr.toFixed(2)}`,
          legendgroup: "gshr-room",
          showlegend: true,
          hoverinfo: "skip",
        });

        const grAdp = gshrResult.room_shr_adp;
        t.push({
          x: [grAdp.Tdb],
          y: [grAdp.W_display],
          mode: "markers",
          type: "scatter",
          marker: { color: SHR_COLORS.room_shr, size: 10, symbol: "star", line: { color: "#fff", width: 1 } },
          name: "Room SHR ADP",
          legendgroup: "gshr-room",
          showlegend: false,
          hovertemplate:
            `<b>Room SHR ADP</b><br>Tdb: ${fmt(grAdp.Tdb, 1)}${gTUnit}<br>` +
            `W: ${fmt(grAdp.W_display, 1)} ${gWUnit}<extra></extra>`,
        });

        t.push({
          x: gshrResult.gshr_line.map((p) => p.Tdb),
          y: gshrResult.gshr_line.map((p) => p.W_display),
          mode: "lines",
          type: "scatter",
          line: { color: SHR_COLORS.gshr, width: 2, dash: "dashdot" },
          name: `GSHR ${gshrResult.gshr.toFixed(2)}`,
          legendgroup: "gshr-grand",
          showlegend: true,
          hoverinfo: "skip",
        });

        const ggAdp = gshrResult.gshr_adp;
        t.push({
          x: [ggAdp.Tdb],
          y: [ggAdp.W_display],
          mode: "markers",
          type: "scatter",
          marker: { color: SHR_COLORS.gshr, size: 10, symbol: "star", line: { color: "#fff", width: 1 } },
          name: "GSHR ADP",
          legendgroup: "gshr-grand",
          showlegend: false,
          hovertemplate:
            `<b>GSHR ADP</b><br>Tdb: ${fmt(ggAdp.Tdb, 1)}${gTUnit}<br>` +
            `W: ${fmt(ggAdp.W_display, 1)} ${gWUnit}<extra></extra>`,
        });

        const mp = gshrResult.mixed_point;
        t.push({
          x: [mp.Tdb],
          y: [mp.W_display],
          mode: "markers",
          type: "scatter",
          marker: { color: SHR_COLORS.gshr, size: 9, symbol: "triangle-up", line: { color: "#fff", width: 1 } },
          name: "Mixed Air",
          legendgroup: "gshr-grand",
          showlegend: false,
          hovertemplate:
            `<b>Mixed Air</b><br>Tdb: ${fmt(mp.Tdb, 1)}${gTUnit}<br>` +
            `RH: ${fmt(mp.RH, 1)}%<br>W: ${fmt(mp.W_display, 1)} ${gWUnit}<extra></extra>`,
        });

        if (gshrResult.eshr_line && gshrResult.eshr != null && gshrResult.eshr_adp) {
          t.push({
            x: gshrResult.eshr_line.map((p) => p.Tdb),
            y: gshrResult.eshr_line.map((p) => p.W_display),
            mode: "lines",
            type: "scatter",
            line: { color: SHR_COLORS.eshr, width: 2, dash: "dot" },
            name: `ESHR ${gshrResult.eshr.toFixed(2)}`,
            legendgroup: "gshr-eff",
            showlegend: true,
            hoverinfo: "skip",
          });

          const geAdp = gshrResult.eshr_adp;
          t.push({
            x: [geAdp.Tdb],
            y: [geAdp.W_display],
            mode: "markers",
            type: "scatter",
            marker: { color: SHR_COLORS.eshr, size: 10, symbol: "star", line: { color: "#fff", width: 1 } },
            name: "ESHR ADP",
            legendgroup: "gshr-eff",
            showlegend: false,
            hovertemplate:
              `<b>ESHR ADP</b><br>Tdb: ${fmt(geAdp.Tdb, 1)}${gTUnit}<br>` +
              `W: ${fmt(geAdp.W_display, 1)} ${gWUnit}<extra></extra>`,
          });
        }
      }
    }

    // --- Design day overlay ---
    if (visibility.designDays && designDayResult && designDayResult.points.length > 0) {
      const ddIsIP = designDayResult.unit_system === "IP";
      const ddTUnit = ddIsIP ? "\u00B0F" : "\u00B0C";
      const ddWUnit = ddIsIP ? "gr/lb" : "g/kg";

      // Separate cooling and heating points for different colors
      const coolingPts = designDayResult.points.filter(p => p.category.startsWith("cooling"));
      const heatingPts = designDayResult.points.filter(p => p.category === "heating");

      if (coolingPts.length > 0) {
        t.push({
          x: coolingPts.map(p => p.Tdb),
          y: coolingPts.map(p => p.W_display),
          mode: "markers",
          type: "scatter",
          marker: {
            color: "#ffa502",
            size: 12,
            symbol: "triangle-up",
            line: { color: "#fff", width: 1.5 },
          },
          name: `Design Day: ${designDayResult.location.name} (Cooling)`,
          legendgroup: "design-day",
          showlegend: true,
          text: coolingPts.map(p => p.condition_label),
          hovertemplate: coolingPts.map(p =>
            `<b>${designDayResult.location.name} - ${p.condition_label}</b><br>` +
            `Tdb: ${fmt(p.Tdb, 1)}${ddTUnit}<br>` +
            `RH: ${fmt(p.RH, 1)}%<br>` +
            `W: ${fmt(p.W_display, 1)} ${ddWUnit}<br>` +
            `Twb: ${fmt(p.Twb, 1)}${ddTUnit}` +
            `<extra></extra>`
          ),
        });
      }

      if (heatingPts.length > 0) {
        t.push({
          x: heatingPts.map(p => p.Tdb),
          y: heatingPts.map(p => p.W_display),
          mode: "markers",
          type: "scatter",
          marker: {
            color: "#70a1ff",
            size: 12,
            symbol: "triangle-down",
            line: { color: "#fff", width: 1.5 },
          },
          name: `Design Day: ${designDayResult.location.name} (Heating)`,
          legendgroup: "design-day",
          showlegend: true,
          text: heatingPts.map(p => p.condition_label),
          hovertemplate: heatingPts.map(p =>
            `<b>${designDayResult.location.name} - ${p.condition_label}</b><br>` +
            `Tdb: ${fmt(p.Tdb, 1)}${ddTUnit}<br>` +
            `RH: ${fmt(p.RH, 1)}%<br>` +
            `W: ${fmt(p.W_display, 1)} ${ddWUnit}` +
            `<extra></extra>`
          ),
        });
      }
    }

    return t;
  }, [chartData, statePoints, processes, coilResult, shrLines, gshrResult, designDayResult, tmyResult, tmyDisplayMode, selectedPointIndex, theme, visibility]);

  // Layout
  const layout = useMemo<Partial<Layout>>(() => {
    const ranges = chartData?.ranges;
    const isIP = unitSystem === "IP";

    // Process direction arrows + numbering labels
    const arrowAnnotations = visibility.processes ? processes.map((proc) => {
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
    }) : [];

    const numberAnnotations = visibility.processes ? processes.map((proc, i) => {
      const pts = proc.path_points;
      const color = PROCESS_COLORS[proc.process_type] ?? "#aaa";
      const midIdx = Math.floor(pts.length / 2);
      const mid = pts[midIdx];
      return {
        x: mid.Tdb,
        y: mid.W_display,
        xref: "x" as const,
        yref: "y" as const,
        text: `<b>${i + 1}</b>`,
        showarrow: false,
        font: { size: 11, color, family: "IBM Plex Sans" },
        bgcolor: COLORS.annotationBg,
        bordercolor: color,
        borderwidth: 1,
        borderpad: 2,
        yshift: 12,
      };
    }) : [];

    // Coil direction arrow
    const coilAnnotations: typeof arrowAnnotations = [];
    if (visibility.coil && coilResult && coilResult.path_points.length > 2) {
      const cpts = coilResult.path_points;
      const cFromIdx = Math.floor(cpts.length * 0.4);
      const cToIdx = Math.floor(cpts.length * 0.6);
      coilAnnotations.push({
        x: cpts[cToIdx].Tdb,
        y: cpts[cToIdx].W_display,
        ax: cpts[cFromIdx].Tdb,
        ay: cpts[cFromIdx].W_display,
        xref: "x" as const,
        yref: "y" as const,
        axref: "x" as const,
        ayref: "y" as const,
        showarrow: true,
        arrowhead: 3,
        arrowsize: 1.5,
        arrowwidth: 2,
        arrowcolor: SHR_COLORS.coil,
        opacity: 0.8,
        text: "",
      });
    }

    const annotations = [...arrowAnnotations, ...numberAnnotations, ...coilAnnotations];

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
        bgcolor: COLORS.legendBg,
        bordercolor: COLORS.grid,
        borderwidth: 1,
        font: { size: 11 },
      },
      hovermode: "closest",
      dragmode: "pan",
      annotations,
    };
  }, [chartData, unitSystem, processes, coilResult, gshrResult, theme, visibility]);

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
    <div className="w-full h-full relative" ref={plotRef}>
      <Plot
        data={traces}
        layout={layout}
        config={config}
        useResizeHandler
        style={{ width: "100%", height: "100%" }}
        onHover={handleHover}
        onUnhover={handleUnhover}
        onClick={handleClick}
      />

      {/* Chart legend / visibility toggles */}
      <ChartLegend />

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
