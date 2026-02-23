import { create } from "zustand";
import type { UnitSystem, ChartData, StatePointOutput, ProcessOutput, CoilOutput, SHRLineOutput, GSHROutput, AirflowCalcOutput, CondensationCheckOutput, DesignDayResolveOutput, TMYProcessOutput, AHUWizardOutput } from "../types/psychro";
import type { ProjectFile } from "../types/project";

// Snapshot of undoable state
interface StateSnapshot {
  statePoints: StatePointOutput[];
  processes: ProcessOutput[];
  coilResult: CoilOutput | null;
  shrLines: SHRLineOutput[];
  gshrResult: GSHROutput | null;
}

// Toast notification
export interface Toast {
  id: string;
  message: string;
  type: "success" | "error" | "warning";
}

// Visibility toggles for chart layers
export interface ChartVisibility {
  rhLines: boolean;
  twbLines: boolean;
  enthalpyLines: boolean;
  volumeLines: boolean;
  statePoints: boolean;
  processes: boolean;
  coil: boolean;
  shrLines: boolean;
  designDays: boolean;
  tmyData: boolean;
}

const MAX_HISTORY = 50;

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

  // --- Phase 7: Design Day overlay ---
  designDayResult: DesignDayResolveOutput | null;
  designDayLoading: boolean;

  // Actions — design day
  setDesignDayResult: (result: DesignDayResolveOutput | null) => void;
  clearDesignDayResult: () => void;
  setDesignDayLoading: (loading: boolean) => void;

  // --- Phase 7: TMY data overlay ---
  tmyResult: TMYProcessOutput | null;
  tmyDisplayMode: "scatter" | "heatmap";
  tmyLoading: boolean;

  // Actions — TMY
  setTMYResult: (result: TMYProcessOutput | null) => void;
  clearTMYResult: () => void;
  setTMYDisplayMode: (mode: "scatter" | "heatmap") => void;
  setTMYLoading: (loading: boolean) => void;

  // --- Phase 7: AHU Wizard ---
  ahuWizardResult: AHUWizardOutput | null;
  ahuWizardLoading: boolean;

  // Actions — AHU Wizard
  setAHUWizardResult: (result: AHUWizardOutput | null) => void;
  clearAHUWizardResult: () => void;
  setAHUWizardLoading: (loading: boolean) => void;
  applyAHUWizardToChart: () => void;

  // --- Phase 6: Project save/load ---
  projectTitle: string;
  setProjectTitle: (title: string) => void;
  exportProject: () => ProjectFile;
  importProject: (data: ProjectFile) => void;
  clearAll: () => void;

  // --- Phase 6: Chart ref for image export ---
  chartRef: HTMLElement | null;
  setChartRef: (el: HTMLElement | null) => void;

  // --- Phase 6: Click-to-add ---
  pendingClickPoint: { Tdb: number; W_display: number } | null;
  setPendingClickPoint: (pt: { Tdb: number; W_display: number } | null) => void;

  // --- Phase 6: Right-click to start process ---
  pendingProcessStartIndex: number | null;
  setPendingProcessStartIndex: (index: number | null) => void;

  // --- Phase 6: Selected state point ---
  selectedPointIndex: number | null;
  setSelectedPointIndex: (index: number | null) => void;

  // --- Phase 6: Undo/redo ---
  _history: StateSnapshot[];
  _future: StateSnapshot[];
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // --- Phase 6: Theme ---
  theme: "dark" | "light";
  toggleTheme: () => void;

  // --- Phase 6: Chart visibility ---
  visibility: ChartVisibility;
  toggleVisibility: (key: keyof ChartVisibility) => void;

  // --- Phase 6: Toasts ---
  toasts: Toast[];
  addToast: (message: string, type: Toast["type"]) => void;
  removeToast: (id: string) => void;
}

function takeSnapshot(state: AppState): StateSnapshot {
  return {
    statePoints: state.statePoints,
    processes: state.processes,
    coilResult: state.coilResult,
    shrLines: state.shrLines,
    gshrResult: state.gshrResult,
  };
}

export const useStore = create<AppState>((set, get) => ({
  // Default settings (IP, sea level)
  unitSystem: "IP",
  pressure: 14.696,
  altitude: 0,

  // Chart
  chartData: null,
  chartLoading: true,
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

  addStatePoint: (sp) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      statePoints: [...state.statePoints, sp],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  removeStatePoint: (index) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      statePoints: state.statePoints.filter((_, i) => i !== index),
      selectedPointIndex: state.selectedPointIndex === index ? null : state.selectedPointIndex,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  clearStatePoints: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      statePoints: [],
      selectedPointIndex: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  // Processes
  processes: [],
  processLoading: false,
  processError: null,

  addProcess: (p) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      processes: [...state.processes, p],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  removeProcess: (index) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      processes: state.processes.filter((_, i) => i !== index),
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  clearProcesses: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      processes: [],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  setProcessLoading: (loading) => set({ processLoading: loading }),
  setProcessError: (error) => set({ processError: error, processLoading: false }),

  // Coil analysis
  coilResult: null,
  coilLoading: false,
  coilError: null,

  setCoilResult: (result) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      coilResult: result,
      coilError: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  setCoilLoading: (loading) => set({ coilLoading: loading }),
  setCoilError: (error) => set({ coilError: error, coilLoading: false }),
  clearCoilResult: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      coilResult: null,
      coilError: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  // SHR lines
  shrLines: [],
  gshrResult: null,

  addSHRLine: (line) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      shrLines: [...state.shrLines, line],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  removeSHRLine: (index) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      shrLines: state.shrLines.filter((_, i) => i !== index),
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  clearSHRLines: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      shrLines: [],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  setGSHRResult: (result) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      gshrResult: result,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },
  clearGSHRResult: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      gshrResult: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  // Airflow calc
  airflowResult: null,
  condensationResult: null,

  setAirflowResult: (result) => set({ airflowResult: result }),
  clearAirflowResult: () => set({ airflowResult: null }),
  setCondensationResult: (result) => set({ condensationResult: result }),
  clearCondensationResult: () => set({ condensationResult: null }),

  // --- Phase 7: Design Day overlay ---
  designDayResult: null,
  designDayLoading: false,

  setDesignDayResult: (result) => set({ designDayResult: result }),
  clearDesignDayResult: () => set({ designDayResult: null }),
  setDesignDayLoading: (loading) => set({ designDayLoading: loading }),

  // --- Phase 7: TMY data overlay ---
  tmyResult: null,
  tmyDisplayMode: "scatter",
  tmyLoading: false,

  setTMYResult: (result) => set({ tmyResult: result }),
  clearTMYResult: () => set({ tmyResult: null }),
  setTMYDisplayMode: (mode) => set({ tmyDisplayMode: mode }),
  setTMYLoading: (loading) => set({ tmyLoading: loading }),

  // --- Phase 7: AHU Wizard ---
  ahuWizardResult: null,
  ahuWizardLoading: false,

  setAHUWizardResult: (result) => set({ ahuWizardResult: result }),
  clearAHUWizardResult: () => set({ ahuWizardResult: null }),
  setAHUWizardLoading: (loading) => set({ ahuWizardLoading: loading }),

  applyAHUWizardToChart: () => {
    const state = get();
    const result = state.ahuWizardResult;
    if (!result) return;

    const snapshot = takeSnapshot(state);

    // Collect all state points from the wizard result
    const newPoints: StatePointOutput[] = [];
    if (result.oa_point) newPoints.push(result.oa_point as StatePointOutput);
    if (result.ra_point) newPoints.push(result.ra_point as StatePointOutput);
    if (result.mixed_point) newPoints.push(result.mixed_point as StatePointOutput);
    if (result.coil_leaving) newPoints.push(result.coil_leaving as StatePointOutput);
    if (result.supply_point && result.needs_reheat) {
      newPoints.push(result.supply_point as StatePointOutput);
    }

    // Collect processes
    const newProcesses = result.processes as ProcessOutput[];

    set({
      statePoints: [...state.statePoints, ...newPoints],
      processes: [...state.processes, ...newProcesses],
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  // --- Phase 6: Project save/load ---
  projectTitle: "Untitled Project",
  setProjectTitle: (title) => set({ projectTitle: title }),

  exportProject: () => {
    const state = get();
    return {
      version: "1.0" as const,
      title: state.projectTitle,
      savedAt: new Date().toISOString(),
      unitSystem: state.unitSystem,
      pressure: state.pressure,
      altitude: state.altitude,
      statePoints: state.statePoints,
      processes: state.processes,
      coilResult: state.coilResult,
      shrLines: state.shrLines,
      gshrResult: state.gshrResult,
    };
  },

  importProject: (data) => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      projectTitle: data.title,
      unitSystem: data.unitSystem,
      pressure: data.pressure,
      altitude: data.altitude,
      statePoints: data.statePoints,
      processes: data.processes,
      coilResult: data.coilResult,
      shrLines: data.shrLines,
      gshrResult: data.gshrResult,
      selectedPointIndex: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  clearAll: () => {
    const state = get();
    const snapshot = takeSnapshot(state);
    set({
      projectTitle: "Untitled Project",
      statePoints: [],
      processes: [],
      coilResult: null,
      shrLines: [],
      gshrResult: null,
      airflowResult: null,
      condensationResult: null,
      designDayResult: null,
      tmyResult: null,
      ahuWizardResult: null,
      selectedPointIndex: null,
      _history: [...state._history, snapshot].slice(-MAX_HISTORY),
      _future: [],
    });
  },

  // --- Phase 6: Chart ref ---
  chartRef: null,
  setChartRef: (el) => set({ chartRef: el }),

  // --- Phase 6: Click-to-add ---
  pendingClickPoint: null,
  setPendingClickPoint: (pt) => set({ pendingClickPoint: pt }),

  // --- Phase 6: Right-click to start process ---
  pendingProcessStartIndex: null,
  setPendingProcessStartIndex: (index) => set({ pendingProcessStartIndex: index }),

  // --- Phase 6: Selected state point ---
  selectedPointIndex: null,
  setSelectedPointIndex: (index) => set({ selectedPointIndex: index }),

  // --- Phase 6: Undo/redo ---
  _history: [],
  _future: [],

  undo: () => {
    const state = get();
    if (state._history.length === 0) return;
    const previous = state._history[state._history.length - 1];
    const currentSnapshot = takeSnapshot(state);
    set({
      ...previous,
      _history: state._history.slice(0, -1),
      _future: [...state._future, currentSnapshot],
    });
  },

  redo: () => {
    const state = get();
    if (state._future.length === 0) return;
    const next = state._future[state._future.length - 1];
    const currentSnapshot = takeSnapshot(state);
    set({
      ...next,
      _future: state._future.slice(0, -1),
      _history: [...state._history, currentSnapshot].slice(-MAX_HISTORY),
    });
  },

  canUndo: () => get()._history.length > 0,
  canRedo: () => get()._future.length > 0,

  // --- Phase 6: Theme ---
  theme: "dark",
  toggleTheme: () => {
    const state = get();
    const newTheme = state.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = newTheme;
    set({ theme: newTheme });
  },

  // --- Phase 6: Chart visibility ---
  visibility: {
    rhLines: true,
    twbLines: true,
    enthalpyLines: true,
    volumeLines: true,
    statePoints: true,
    processes: true,
    coil: true,
    shrLines: true,
    designDays: true,
    tmyData: true,
  },
  toggleVisibility: (key) =>
    set((state) => ({
      visibility: { ...state.visibility, [key]: !state.visibility[key] },
    })),

  // --- Phase 6: Toasts ---
  toasts: [],
  addToast: (message, type) => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    set((state) => ({
      toasts: [...state.toasts, { id, message, type }],
    }));
    setTimeout(() => {
      get().removeToast(id);
    }, 4000);
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));
