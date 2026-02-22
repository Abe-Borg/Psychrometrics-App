import { useRef } from "react";
import { useStore } from "../../store/useStore";
import { uploadTMYFile } from "../../api/client";

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
    addToast,
  } = useStore();

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

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
      // Reset file input so same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleClear = () => {
    clearTMYResult();
  };

  return (
    <div className="flex flex-col gap-3">
      {/* File upload */}
      <div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileSelect}
          className="hidden"
          id="tmy-upload"
        />
        <label
          htmlFor="tmy-upload"
          className={`block w-full text-center px-3 py-2 text-sm rounded border border-dashed
                     border-border text-text-secondary hover:text-text-primary hover:border-accent
                     cursor-pointer transition-colors ${tmyLoading ? "opacity-50 pointer-events-none" : ""}`}
        >
          {tmyLoading ? "Processing..." : "Upload TMY3 CSV"}
        </label>
      </div>

      {/* Controls (shown when data loaded) */}
      {tmyResult && (
        <>
          <div className="text-xs text-text-muted">
            {tmyResult.location_name ?? "TMY Data"} &mdash; {tmyResult.total_hours} hours
          </div>

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
          </div>

          {/* Clear button */}
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-sm rounded border border-border text-text-secondary hover:text-text-primary"
          >
            Clear TMY Data
          </button>
        </>
      )}
    </div>
  );
}
