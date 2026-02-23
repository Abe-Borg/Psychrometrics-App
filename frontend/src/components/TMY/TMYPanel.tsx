import { useRef, useState } from "react";
import { useStore } from "../../store/useStore";
import { uploadTMYFile, analyzeWeatherFile } from "../../api/client";
import { fmt } from "../../utils/formatting";

export default function TMYPanel() {
  const {
    unitSystem,
    pressure,
    tmyResult,
    tmyDisplayMode,
    tmyLoading,
    setTMYResult,
    clearTMYResult,
    setTMYDisplayMode,
    setTMYLoading,
    weatherAnalysis,
    weatherAnalysisLoading,
    setWeatherAnalysis,
    clearWeatherAnalysis,
    setWeatherAnalysisLoading,
    addToast,
  } = useStore();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const epwFileRef = useRef<File | null>(null);
  const [clusterCount, setClusterCount] = useState(5);

  const isLoading = tmyLoading || weatherAnalysisLoading;

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isEpw = file.name.toLowerCase().endsWith(".epw");
    if (isEpw) epwFileRef.current = file;

    // Always run the TMY upload for scatter/heatmap data
    setTMYLoading(true);
    try {
      const result = await uploadTMYFile(file, unitSystem, pressure);
      setTMYResult(result);
      addToast(
        `Loaded ${result.total_hours} hours from ${result.location_name ?? file.name}`,
        "success"
      );
    } catch (err) {
      addToast(err instanceof Error ? err.message : "Failed to process TMY file", "error");
    } finally {
      setTMYLoading(false);
    }

    // For EPW files, also run weather analysis (clustering + design points)
    if (isEpw) {
      setWeatherAnalysisLoading(true);
      try {
        const analysis = await analyzeWeatherFile(file, unitSystem, clusterCount);
        setWeatherAnalysis(analysis);
        addToast(
          `Weather analysis complete: ${analysis.design_points.length} design points extracted`,
          "success"
        );
      } catch (err) {
        addToast(
          err instanceof Error ? err.message : "Failed to analyze weather file",
          "error"
        );
      } finally {
        setWeatherAnalysisLoading(false);
      }
    }

    // Reset file input so same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleReanalyze = async () => {
    const file = epwFileRef.current;
    if (!file) {
      addToast("Re-upload the EPW file to change cluster count", "warning");
      return;
    }
    setWeatherAnalysisLoading(true);
    try {
      const analysis = await analyzeWeatherFile(file, unitSystem, clusterCount);
      setWeatherAnalysis(analysis);
      addToast(
        `Re-analyzed with ${clusterCount} clusters: ${analysis.design_points.length} design points`,
        "success"
      );
    } catch (err) {
      addToast(
        err instanceof Error ? err.message : "Failed to re-analyze weather file",
        "error"
      );
    } finally {
      setWeatherAnalysisLoading(false);
    }
  };

  const handleClear = () => {
    clearTMYResult();
    clearWeatherAnalysis();
    epwFileRef.current = null;
  };

  const hasData = tmyResult || weatherAnalysis;
  const showClustersOption = weatherAnalysis !== null;

  return (
    <div className="flex flex-col gap-3">
      {/* File upload — always visible */}
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.epw"
          onChange={handleFileSelect}
          className="hidden"
          id="tmy-upload"
        />
        <label
          htmlFor="tmy-upload"
          className={`block w-full text-center px-3 py-2 text-sm rounded border border-dashed
                     border-border text-text-secondary hover:text-text-primary hover:border-accent
                     cursor-pointer transition-colors ${isLoading ? "opacity-50 pointer-events-none" : ""}`}
        >
          {isLoading ? "Processing..." : "Upload Weather File (CSV / EPW)"}
        </label>
      </div>

      {/* Controls (shown when data loaded) */}
      {hasData && (
        <>
          {/* Location metadata */}
          {weatherAnalysis && (
            <div className="text-xs text-text-muted space-y-0.5">
              <div className="font-medium text-text-secondary">
                {weatherAnalysis.location.city}
                {weatherAnalysis.location.state ? `, ${weatherAnalysis.location.state}` : ""}
              </div>
              <div>
                Elev: {fmt(weatherAnalysis.location.elevation, 0)}{" "}
                {unitSystem === "IP" ? "m" : "m"} &middot;{" "}
                {weatherAnalysis.total_hours} hours &middot;{" "}
                {weatherAnalysis.design_points.length} design pts
              </div>
            </div>
          )}

          {!weatherAnalysis && tmyResult && (
            <div className="text-xs text-text-muted">
              {tmyResult.location_name ?? "TMY Data"} &mdash; {tmyResult.total_hours} hours
            </div>
          )}

          {/* Display mode toggle */}
          <div className="flex gap-1">
            <button
              onClick={() => setTMYDisplayMode("scatter")}
              className={`flex-1 px-2 py-1 text-xs rounded ${
                tmyDisplayMode === "scatter"
                  ? "bg-accent text-white"
                  : "bg-bg-primary border border-border text-text-secondary hover:text-text-primary"
              }`}
            >
              Scatter
            </button>
            <button
              onClick={() => setTMYDisplayMode("heatmap")}
              className={`flex-1 px-2 py-1 text-xs rounded ${
                tmyDisplayMode === "heatmap"
                  ? "bg-accent text-white"
                  : "bg-bg-primary border border-border text-text-secondary hover:text-text-primary"
              }`}
            >
              Heatmap
            </button>
            {showClustersOption && (
              <button
                onClick={() => setTMYDisplayMode("clusters")}
                className={`flex-1 px-2 py-1 text-xs rounded ${
                  tmyDisplayMode === "clusters"
                    ? "bg-accent text-white"
                    : "bg-bg-primary border border-border text-text-secondary hover:text-text-primary"
                }`}
              >
                Clusters
              </button>
            )}
          </div>

          {/* Cluster controls (shown in clusters mode) */}
          {tmyDisplayMode === "clusters" && weatherAnalysis && (
            <div className="flex flex-col gap-2 p-2 rounded bg-bg-primary border border-border">
              <div className="flex items-center justify-between">
                <label className="text-xs text-text-secondary" htmlFor="cluster-count">
                  Clusters: {clusterCount}
                </label>
                <button
                  onClick={handleReanalyze}
                  className="px-2 py-0.5 text-xs rounded bg-accent text-white hover:bg-accent/80 transition-colors"
                >
                  Re-analyze
                </button>
              </div>
              <input
                id="cluster-count"
                type="range"
                min={3}
                max={10}
                value={clusterCount}
                onChange={(e) => setClusterCount(Number(e.target.value))}
                className="w-full accent-accent"
              />

              {/* Cluster summary */}
              <div className="text-xs text-text-muted space-y-0.5">
                {weatherAnalysis.cluster_summary.map((c) => (
                  <div key={c.cluster_id} className="flex justify-between">
                    <span>{c.label}</span>
                    <span>{c.hour_count} hrs ({fmt(c.fraction_of_year * 100, 0)}%)</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Loading indicator for weather analysis */}
          {weatherAnalysisLoading && (
            <div className="text-xs text-text-muted italic">
              Analyzing weather patterns...
            </div>
          )}

          {/* Clear button */}
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-sm rounded border border-border text-text-secondary hover:text-text-primary"
          >
            Clear Weather Data
          </button>
        </>
      )}
    </div>
  );
}
