import { useState, useCallback, useRef, useEffect } from "react";
import { useStore } from "../../store/useStore";
import { searchDesignDayLocations, resolveDesignDayConditions } from "../../api/client";
import { fmt } from "../../utils/formatting";
import type { DesignDaySearchResult } from "../../types/psychro";

export default function DesignDayPanel() {
  const {
    unitSystem,
    pressure,
    designDayResult,
    designDayLoading,
    setDesignDayResult,
    setDesignDayLoading,
    clearDesignDayResult,
    addToast,
  } = useStore();

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<DesignDaySearchResult[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState<DesignDaySearchResult | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSearch = useCallback(
    (value: string) => {
      setQuery(value);
      if (debounceRef.current) clearTimeout(debounceRef.current);

      if (value.trim().length === 0) {
        setSearchResults([]);
        setShowDropdown(false);
        return;
      }

      debounceRef.current = setTimeout(async () => {
        try {
          const results = await searchDesignDayLocations(value, 10);
          setSearchResults(results);
          setShowDropdown(results.length > 0);
        } catch {
          setSearchResults([]);
        }
      }, 250);
    },
    []
  );

  const handleSelectLocation = (loc: DesignDaySearchResult) => {
    setSelectedLocation(loc);
    setQuery(`${loc.name}, ${loc.state}`);
    setShowDropdown(false);
  };

  const handleLoad = async () => {
    if (!selectedLocation) return;
    setDesignDayLoading(true);
    try {
      const result = await resolveDesignDayConditions({
        location_name: selectedLocation.name,
        location_state: selectedLocation.state,
        condition_labels: [],
        unit_system: unitSystem,
        pressure,
      });
      setDesignDayResult(result);
      addToast(`Loaded ${result.points.length} design conditions for ${selectedLocation.name}`, "success");
    } catch (e) {
      addToast(e instanceof Error ? e.message : "Failed to load design day data", "error");
    } finally {
      setDesignDayLoading(false);
    }
  };

  const handleClear = () => {
    clearDesignDayResult();
    setSelectedLocation(null);
    setQuery("");
  };

  const isIP = unitSystem === "IP";
  const tUnit = isIP ? "\u00B0F" : "\u00B0C";
  const wUnit = isIP ? "gr/lb" : "g/kg";

  return (
    <div className="flex flex-col gap-3">
      {/* Search input */}
      <div className="relative" ref={dropdownRef}>
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          onFocus={() => { if (searchResults.length > 0) setShowDropdown(true); }}
          placeholder="Search city..."
          className="w-full px-3 py-2 rounded bg-bg-primary border border-border text-text-primary text-sm
                     focus:outline-none focus:border-accent"
        />

        {showDropdown && searchResults.length > 0 && (
          <div className="absolute z-50 w-full mt-1 bg-bg-secondary border border-border rounded shadow-lg max-h-48 overflow-y-auto">
            {searchResults.map((loc) => (
              <button
                key={`${loc.name}-${loc.state}`}
                onClick={() => handleSelectLocation(loc)}
                className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-accent/20 flex justify-between"
              >
                <span>{loc.name}, {loc.state}</span>
                <span className="text-text-muted text-xs">CZ {loc.climate_zone}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Location info */}
      {selectedLocation && (
        <div className="text-xs text-text-muted">
          {selectedLocation.name}, {selectedLocation.state} &mdash; CZ {selectedLocation.climate_zone} &mdash; {fmt(selectedLocation.elevation_ft, 0)} ft
        </div>
      )}

      {/* Load / Clear buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleLoad}
          disabled={!selectedLocation || designDayLoading}
          className="flex-1 px-3 py-1.5 text-sm rounded bg-accent text-white hover:bg-accent/80
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {designDayLoading ? "Loading..." : "Load Conditions"}
        </button>
        {designDayResult && (
          <button
            onClick={handleClear}
            className="px-3 py-1.5 text-sm rounded border border-border text-text-secondary hover:text-text-primary"
          >
            Clear
          </button>
        )}
      </div>

      {/* Results summary */}
      {designDayResult && (
        <div className="flex flex-col gap-1">
          <div className="text-xs font-semibold text-text-secondary">
            {designDayResult.location.name}, {designDayResult.location.state} &mdash; {designDayResult.points.length} conditions
          </div>
          <div className="max-h-40 overflow-y-auto">
            {designDayResult.points.map((pt, i) => (
              <div
                key={i}
                className="flex justify-between text-xs py-0.5 border-b border-border/50"
              >
                <span className="text-text-muted truncate mr-2">{pt.condition_label}</span>
                <span className="text-text-primary whitespace-nowrap">
                  {fmt(pt.Tdb, 1)}{tUnit} / {fmt(pt.W_display, 1)} {wUnit}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
