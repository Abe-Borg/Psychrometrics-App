import { create } from "zustand";
import type { UnitSystem, ChartData, StatePointOutput } from "../types/psychro";

interface AppState {
  // Settings
  unitSystem: UnitSystem;
  pressure: number;
  altitude: number;

  // Chart data
  chartData: ChartData | null;
  chartLoading: boolean;
  chartError: string | null;

  // State points
  statePoints: StatePointOutput[];

  // Actions — settings
  setUnitSystem: (us: UnitSystem) => void;
  setPressure: (p: number) => void;
  setAltitude: (a: number) => void;

  // Actions — chart
  setChartData: (data: ChartData) => void;
  setChartLoading: (loading: boolean) => void;
  setChartError: (error: string | null) => void;

  // Actions — state points
  addStatePoint: (sp: StatePointOutput) => void;
  removeStatePoint: (index: number) => void;
  clearStatePoints: () => void;
}

export const useStore = create<AppState>((set) => ({
  // Default settings (IP, sea level)
  unitSystem: "IP",
  pressure: 14.696,
  altitude: 0,

  // Chart
  chartData: null,
  chartLoading: false,
  chartError: null,

  // State points
  statePoints: [],

  // Actions
  setUnitSystem: (us) => set({ unitSystem: us }),
  setPressure: (p) => set({ pressure: p }),
  setAltitude: (a) => set({ altitude: a }),

  setChartData: (data) => set({ chartData: data, chartError: null }),
  setChartLoading: (loading) => set({ chartLoading: loading }),
  setChartError: (error) => set({ chartError: error, chartLoading: false }),

  addStatePoint: (sp) =>
    set((state) => ({ statePoints: [...state.statePoints, sp] })),
  removeStatePoint: (index) =>
    set((state) => ({
      statePoints: state.statePoints.filter((_, i) => i !== index),
    })),
  clearStatePoints: () => set({ statePoints: [] }),
}));
