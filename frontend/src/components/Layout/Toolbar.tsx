import { useState, useRef } from "react";
import { useStore } from "../../store/useStore";
import { getPressureFromAltitude } from "../../api/client";
import { downloadJSON, downloadCSV, downloadChartImage } from "../../utils/exportHelpers";
import { generateReport } from "../../api/client";
import type { ProjectFile } from "../../types/project";
import Plotly from "plotly.js-dist-min";
import type { PlotlyHTMLElement } from "plotly.js";

export default function Toolbar() {
  const {
    unitSystem, pressure, altitude,
    setUnitSystem, setPressure, setAltitude, clearProcesses,
    projectTitle, setProjectTitle, exportProject, importProject,
    chartRef, statePoints, processes,
    coilResult, shrLines, gshrResult,
    undo, redo, canUndo, canRedo,
    theme, toggleTheme,
    addToast,
  } = useStore();

  const [altInput, setAltInput] = useState(altitude.toString());
  const [pressInput, setPressInput] = useState(pressure.toFixed(3));
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState(projectTitle);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      addToast(e instanceof Error ? e.message : "Failed to convert altitude", "error");
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

  function handleTitleSubmit() {
    setProjectTitle(titleInput.trim() || "Untitled Project");
    setEditingTitle(false);
  }

  function handleSave() {
    const data = exportProject();
    const filename = `${data.title.replace(/[^a-zA-Z0-9_-]/g, "_")}.json`;
    downloadJSON(data, filename);
    addToast("Project saved", "success");
  }

  function handleLoad() {
    fileInputRef.current?.click();
  }

  function handleFileLoaded(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result as string) as ProjectFile;
        if (!data.version || !data.statePoints) {
          throw new Error("Invalid project file format");
        }
        importProject(data);
        setTitleInput(data.title);
        setAltInput(data.altitude.toString());
        setPressInput(data.pressure.toFixed(data.unitSystem === "IP" ? 3 : 0));
        addToast("Project loaded", "success");
      } catch (err) {
        addToast(err instanceof Error ? err.message : "Failed to load project", "error");
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be reloaded
    e.target.value = "";
  }

  async function handleExportImage(format: "png" | "svg") {
    setShowExportMenu(false);
    if (!chartRef) {
      addToast("Chart not ready for export", "error");
      return;
    }
    try {
      const filename = `${projectTitle.replace(/[^a-zA-Z0-9_-]/g, "_")}_chart`;
      await downloadChartImage(chartRef, format, filename);
      addToast(`Chart exported as ${format.toUpperCase()}`, "success");
    } catch {
      addToast("Failed to export chart image", "error");
    }
  }

  function handleExportCSV() {
    setShowExportMenu(false);
    const isIP = unitSystem === "IP";
    const tUnit = isIP ? "°F" : "°C";
    const wUnit = isIP ? "gr/lb" : "g/kg";
    const hUnit = isIP ? "BTU/lb" : "kJ/kg";
    const vUnit = isIP ? "ft³/lb" : "m³/kg";

    // State points CSV
    const spHeaders = ["Label", `Tdb (${tUnit})`, `Twb (${tUnit})`, `Tdp (${tUnit})`, "RH (%)", `W (${wUnit})`, `h (${hUnit})`, `v (${vUnit})`];
    const spRows = statePoints.map((sp, i) => [
      sp.label || `Point ${i + 1}`,
      sp.Tdb.toFixed(2),
      sp.Twb.toFixed(2),
      sp.Tdp.toFixed(2),
      sp.RH.toFixed(1),
      sp.W_display.toFixed(2),
      sp.h.toFixed(2),
      sp.v.toFixed(4),
    ]);

    // Processes CSV (appended below state points)
    const procHeaders = ["Process", "Type", `Start Tdb (${tUnit})`, `End Tdb (${tUnit})`, `Start W (${wUnit})`, `End W (${wUnit})`];
    const procRows = processes.map((p, i) => [
      `Process ${i + 1}`,
      p.process_type,
      p.start_point.Tdb.toFixed(2),
      p.end_point.Tdb.toFixed(2),
      p.start_point.W_display.toFixed(2),
      p.end_point.W_display.toFixed(2),
    ]);

    // Combine: state points section, then empty row, then processes section
    const allHeaders = spHeaders.length >= procHeaders.length ? spHeaders : procHeaders;
    const padRow = (row: string[], targetLen: number) => {
      while (row.length < targetLen) row.push("");
      return row;
    };

    const rows = [
      ...spRows.map((r) => padRow(r, allHeaders.length)),
      padRow([], allHeaders.length), // empty separator
      padRow(["--- Processes ---"], allHeaders.length),
      padRow(procHeaders, allHeaders.length),
      ...procRows.map((r) => padRow(r, allHeaders.length)),
    ];

    const filename = `${projectTitle.replace(/[^a-zA-Z0-9_-]/g, "_")}_data.csv`;
    downloadCSV(allHeaders, rows, filename);
    addToast("Data exported as CSV", "success");
  }

  async function handleExportPDF() {
    setShowExportMenu(false);
    if (!chartRef) {
      addToast("Chart not ready for PDF export", "error");
      return;
    }
    try {
      addToast("Generating PDF report...", "success");
      // Capture chart as base64 PNG
      const imgData = await Plotly.toImage(chartRef as PlotlyHTMLElement, {
        format: "png",
        width: 1600,
        height: 900,
      });
      const payload = {
        title: projectTitle,
        unit_system: unitSystem,
        pressure,
        altitude,
        chart_image_base64: imgData,
        state_points: statePoints,
        processes,
        coil_result: coilResult,
        shr_lines: shrLines,
        gshr_result: gshrResult,
        include_sections: [
          "chart",
          ...(statePoints.length > 0 ? ["state_points"] : []),
          ...(processes.length > 0 ? ["processes"] : []),
          ...(coilResult ? ["coil"] : []),
          ...(shrLines.length > 0 || gshrResult ? ["shr"] : []),
        ],
      };
      const blob = await generateReport(payload);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${projectTitle.replace(/[^a-zA-Z0-9_-]/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      addToast("PDF report downloaded", "success");
    } catch (err) {
      addToast(err instanceof Error ? err.message : "Failed to generate PDF", "error");
    }
  }

  return (
    <div className="toolbar-bar flex items-center gap-3 px-4 py-2 bg-bg-secondary border-b border-border text-sm">
      {/* Project title */}
      {editingTitle ? (
        <input
          type="text"
          value={titleInput}
          onChange={(e) => setTitleInput(e.target.value)}
          onBlur={handleTitleSubmit}
          onKeyDown={(e) => e.key === "Enter" && handleTitleSubmit()}
          autoFocus
          className="px-2 py-0.5 bg-bg-tertiary border border-accent rounded text-text-primary
                     text-sm font-semibold focus:outline-none w-44"
        />
      ) : (
        <button
          onClick={() => { setTitleInput(projectTitle); setEditingTitle(true); }}
          className="font-semibold text-text-primary tracking-wide hover:text-accent transition-colors cursor-pointer truncate max-w-44"
          title="Click to rename project"
        >
          {projectTitle}
        </button>
      )}

      <div className="w-px h-5 bg-border" />

      {/* Save / Load */}
      <button onClick={handleSave} className="toolbar-btn" title="Save project (Ctrl+S)">
        Save
      </button>
      <button onClick={handleLoad} className="toolbar-btn" title="Load project">
        Load
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={handleFileLoaded}
      />

      {/* Export dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowExportMenu(!showExportMenu)}
          className="toolbar-btn"
          title="Export chart or data"
        >
          Export &#9662;
        </button>
        {showExportMenu && (
          <div className="absolute top-full left-0 mt-1 bg-bg-secondary border border-border rounded shadow-lg z-50 min-w-[140px]">
            <button onClick={() => handleExportImage("png")} className="export-menu-item">
              Chart as PNG
            </button>
            <button onClick={() => handleExportImage("svg")} className="export-menu-item">
              Chart as SVG
            </button>
            <button onClick={handleExportCSV} className="export-menu-item">
              Data as CSV
            </button>
            <div className="h-px bg-border" />
            <button onClick={handleExportPDF} className="export-menu-item">
              PDF Report
            </button>
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-border" />

      {/* Undo / Redo */}
      <button
        onClick={undo}
        disabled={!canUndo()}
        className="toolbar-btn disabled:opacity-30 disabled:cursor-not-allowed"
        title="Undo (Ctrl+Z)"
      >
        &#8630;
      </button>
      <button
        onClick={redo}
        disabled={!canRedo()}
        className="toolbar-btn disabled:opacity-30 disabled:cursor-not-allowed"
        title="Redo (Ctrl+Shift+Z)"
      >
        &#8631;
      </button>

      <div className="w-px h-5 bg-border" />

      {/* Unit system toggle */}
      <button
        onClick={handleUnitToggle}
        className="toolbar-btn"
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

      {/* Spacer */}
      <div className="flex-1" />

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="toolbar-btn text-lg"
        title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      >
        {theme === "dark" ? "\u2600" : "\u263D"}
      </button>
    </div>
  );
}
