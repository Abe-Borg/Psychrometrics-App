import { create } from "zustand";
import type { UnitSystem, ChartData, StatePointOutput, ProcessOutput, CoilOutput, SHRLineOutput, GSHROutput, AirflowCalcOutput, CondensationCheckOutput } from "../types/psychro";

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

  // Processes
  processes: ProcessOutput[];
  processLoading: boolean;
  processError: string | null;

  // Actions — processes
  addProcess: (p: ProcessOutput) => void;
  removeProcess: (index: number) => void;
  clearProcesses: () => void;
  setProcessLoading: (loading: boolean) => void;
  setProcessError: (error: string | null) => void;

  // Coil analysis
  coilResult: CoilOutput | null;
  coilLoading: boolean;
  coilError: string | null;

  // Actions — coil
  setCoilResult: (result: CoilOutput | null) => void;
  setCoilLoading: (loading: boolean) => void;
  setCoilError: (error: string | null) => void;
  clearCoilResult: () => void;

  // SHR lines
  shrLines: SHRLineOutput[];
  gshrResult: GSHROutput | null;

  // Actions — SHR
  addSHRLine: (line: SHRLineOutput) => void;
  removeSHRLine: (index: number) => void;
  clearSHRLines: () => void;
  setGSHRResult: (result: GSHROutput | null) => void;
  clearGSHRResult: () => void;

  // Airflow calc
  airflowResult: AirflowCalcOutput | null;
  condensationResult: CondensationCheckOutput | null;

  // Actions — airflow
  setAirflowResult: (result: AirflowCalcOutput | null) => void;
  clearAirflowResult: () => void;
  setCondensationResult: (result: CondensationCheckOutput | null) => void;
  clearCondensationResult: () => void;
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

  // Processes
  processes: [],
  processLoading: false,
  processError: null,

  addProcess: (p) =>
    set((state) => ({ processes: [...state.processes, p] })),
  removeProcess: (index) =>
    set((state) => ({
      processes: state.processes.filter((_, i) => i !== index),
    })),
  clearProcesses: () => set({ processes: [] }),
  setProcessLoading: (loading) => set({ processLoading: loading }),
  setProcessError: (error) => set({ processError: error, processLoading: false }),

  // Coil analysis
  coilResult: null,
  coilLoading: false,
  coilError: null,

  setCoilResult: (result) => set({ coilResult: result, coilError: null }),
  setCoilLoading: (loading) => set({ coilLoading: loading }),
  setCoilError: (error) => set({ coilError: error, coilLoading: false }),
  clearCoilResult: () => set({ coilResult: null, coilError: null }),

  // SHR lines
  shrLines: [],
  gshrResult: null,

  addSHRLine: (line) =>
    set((state) => ({ shrLines: [...state.shrLines, line] })),
  removeSHRLine: (index) =>
    set((state) => ({
      shrLines: state.shrLines.filter((_, i) => i !== index),
    })),
  clearSHRLines: () => set({ shrLines: [] }),
  setGSHRResult: (result) => set({ gshrResult: result }),
  clearGSHRResult: () => set({ gshrResult: null }),

  // Airflow calc
  airflowResult: null,
  condensationResult: null,

  setAirflowResult: (result) => set({ airflowResult: result }),
  clearAirflowResult: () => set({ airflowResult: null }),
  setCondensationResult: (result) => set({ condensationResult: result }),
  clearCondensationResult: () => set({ condensationResult: null }),
}));
