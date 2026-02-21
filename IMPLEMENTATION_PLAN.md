# PsychroApp — Implementation Plan (Chunked)

Each chunk is a self-contained unit of work that results in something testable and runnable. Chunks are ordered by dependency — each one builds on the last.

---

## PHASE 1: Foundation (State Points + Base Chart) ✅ COMPLETE

### Chunk 1.1 — Backend Scaffolding + State Point Engine ✅

**Goal:** A running FastAPI server that can resolve any state point from a valid input pair.

**What was built:**
- FastAPI project with virtual environment, psychrolib, pydantic, scipy, numpy
- `config.py` with UnitSystem enum, constants, chart ranges, supported input pairs
- Pydantic models: `StatePointInput`, `StatePointOutput` (11 resolved properties)
- `state_resolver.py` with 7 input pairs (Tdb+RH, Tdb+Twb, Tdb+Tdp, Tdb+W, Tdb+h, Twb+RH, Tdp+RH)
- Iterative solvers using scipy.optimize.brentq for pairs psychrolib can't handle directly
- Dispatch table with automatic reverse-order pair handling
- `POST /api/v1/state-point` and `GET /api/v1/pressure-from-altitude` endpoints
- 50 passing tests validating against ASHRAE reference data

---

### Chunk 1.2 — Chart Background Data Generator ✅

**Goal:** An endpoint that returns all the data needed to draw the psychrometric chart background.

**What was built:**
- `chart_generator.py` with generators for: saturation curve (200 pts), 9 RH lines (10%-90%), 12 Twb lines, 10 enthalpy lines, 6 specific volume lines
- All generators use numpy.linspace for sweeps, psychrolib for calculations
- Automatic altitude/pressure adjustment
- `GET /api/v1/chart-data` endpoint returning all line sets as JSON
- 29 passing tests (saturation accuracy, RH ordering, physics validation, SI support, Denver altitude case)

---

### Chunk 1.3 — Frontend Scaffolding + Base Chart Rendering ✅

**Goal:** A React app that fetches chart data and renders an interactive psychrometric chart.

**What was built:**
- Vite + React + TypeScript + Tailwind CSS v4 + Plotly.js + Zustand
- `api/client.ts` with fetch wrappers for all backend endpoints
- TypeScript interfaces mirroring backend models
- `PsychroChart.tsx`: all background lines rendered with color-coding (red saturation, blue RH, green Twb, yellow enthalpy, purple volume)
- Dark theme with custom CSS variables
- Zoom, pan, scroll-zoom enabled
- `AppLayout.tsx` (toolbar + chart + sidebar), `Toolbar.tsx` (unit toggle, altitude, pressure), `Sidebar.tsx`
- Zustand store managing unitSystem, pressure, altitude, chartData, statePoints
- Vite dev server with API proxy to backend

---

### Chunk 1.4 — State Point UI (Input, Display, Plot) ✅

**Goal:** User can define state points via a form, see them plotted on the chart, and view full properties.

**What was built:**
- `StatePointForm.tsx`: dropdown for 7 input pair types, two numeric inputs with dynamic labels/units, optional label, validation, calls backend API
- `StatePointList.tsx`: expandable cards showing all 11 properties, color-coded dots matching chart markers, delete/clear-all
- State points plotted as colored markers with labels on chart
- Hover over markers shows full property tooltips
- 8-color cycle for multiple points

---

### Chunk 1.5 — Hover Tooltip (Live Properties at Cursor) ✅

**Goal:** Real-time psychrometric properties displayed at cursor position.

**What was built:**
- Installed `psychrolib` npm package (JS port) for client-side calculations
- `hoverCalc.ts`: `calcPropertiesAtCursor()` using psychrolib.js — no API round-trip
- `psychrolib.d.ts`: TypeScript declarations for the JS module
- Invisible scatter mesh trace (sampled from RH lines + saturation curve) for hover detection
- Floating tooltip overlay positioned near cursor showing 7 properties in 2-column grid
- Returns null if cursor is above saturation curve (invalid region)

---

**PHASE 1 COMPLETE — 79 passing tests, full interactive chart with state points and live tooltips**

---

## PHASE 2: Core Processes ← START HERE

### Chunk 2.1 — Process Solver Framework + Sensible Heating/Cooling

**Goal:** Establish the process solver pattern and implement the simplest process type.

#### Data Models

New file: `backend/app/models/process.py`

```python
from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional
from app.config import UnitSystem, DEFAULT_PRESSURE_IP

class ProcessType(str, Enum):
    SENSIBLE_HEATING = "sensible_heating"
    SENSIBLE_COOLING = "sensible_cooling"
    COOLING_DEHUMIDIFICATION = "cooling_dehumidification"

class SensibleMode(str, Enum):
    TARGET_TDB = "target_tdb"        # User provides target dry-bulb temperature
    DELTA_T = "delta_t"              # User provides temperature change
    HEAT_AND_AIRFLOW = "heat_and_airflow"  # User provides Q (BTU/hr or W) + CFM (or m³/s)

class ProcessInput(BaseModel):
    """Input for a psychrometric process calculation."""
    process_type: ProcessType
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

    # Start state: resolved from an input pair (reuses existing resolver)
    start_point_pair: tuple[str, str]
    start_point_values: tuple[float, float]

    # Process parameters — which fields are used depends on process_type
    # Sensible heating/cooling:
    sensible_mode: Optional[SensibleMode] = None
    target_Tdb: Optional[float] = None        # for TARGET_TDB mode
    delta_T: Optional[float] = None            # for DELTA_T mode (positive = heating, negative = cooling)
    Q_sensible: Optional[float] = None         # BTU/hr (IP) or W (SI) — for HEAT_AND_AIRFLOW mode
    airflow_cfm: Optional[float] = None        # CFM (IP) or m³/s (SI)

    # Cooling & dehumidification (Chunk 2.2):
    adp_Tdb: Optional[float] = None            # ADP dry-bulb (forward mode)
    bypass_factor: Optional[float] = None      # Bypass factor 0-1 (forward mode)
    leaving_Tdb: Optional[float] = None        # Leaving conditions (reverse mode)
    leaving_RH: Optional[float] = None         # Leaving RH % (reverse mode)

class PathPoint(BaseModel):
    """A point along a process path for chart rendering."""
    Tdb: float
    W: float
    W_display: float

class ProcessOutput(BaseModel):
    """Result of a process calculation."""
    process_type: ProcessType
    unit_system: UnitSystem
    pressure: float

    start_point: dict    # Full StatePointOutput as dict
    end_point: dict      # Full StatePointOutput as dict
    path_points: list[PathPoint]

    # Process metadata (content depends on process_type)
    metadata: dict = Field(default_factory=dict)
    # Sensible: {Qs, delta_T, cfm (if provided)}
    # Cooling/dehum: {ADP_Tdb, ADP_W, BF, CF, Qs, Ql, Qt, SHR}

    warnings: list[str] = Field(default_factory=list)
```

#### Process Solver Base

New file: `backend/app/engine/processes/base.py`

```python
from abc import ABC, abstractmethod
from app.models.process import ProcessInput, ProcessOutput

class ProcessSolver(ABC):
    @abstractmethod
    def solve(self, input: ProcessInput) -> ProcessOutput:
        """Solve the process and return the result."""
        ...
```

#### Sensible Heating/Cooling Solver

New file: `backend/app/engine/processes/sensible.py`

Sensible heating/cooling is a horizontal line on the psychrometric chart (constant W). Three input modes:

1. **TARGET_TDB**: Given start state + target dry-bulb → end state at same W, new Tdb
2. **DELTA_T**: Given start state + ΔT → end state at Tdb + ΔT, same W
3. **HEAT_AND_AIRFLOW**: Given start state + Q (BTU/hr) + CFM → compute ΔT = Q / (C × CFM), then same as DELTA_T
   - C = 1.08 (IP, at sea level) or derived from ρ × cp at actual conditions
   - Altitude correction: C = 60 × ρ × cp where ρ = 1/v

**Edge case: Sensible cooling crosses dew point.** If the target Tdb < start Tdp, the process would cross the dew point, meaning dehumidification would occur in practice. The solver should:
- Complete the calculation as requested (return the state at target Tdb, same W)
- Add a warning to `ProcessOutput.warnings`: "Target Tdb ({target}) is below the dew point ({Tdp}). In practice, dehumidification would occur. Consider using a cooling & dehumidification process."

**Path:** `[start_point, end_point]` — just two points (horizontal line).

**Metadata:** `{Qs: float, delta_T: float, cfm: float | null}`

#### API Route

New file: `backend/app/api/process.py`

- `POST /api/v1/process` — dispatches to correct solver based on `process_type`
- Register in `router.py`

#### Tasks
- [ ] Create `backend/app/models/process.py` with ProcessType, ProcessInput, ProcessOutput
- [ ] Create `backend/app/engine/processes/base.py` with abstract solver
- [ ] Create `backend/app/engine/processes/sensible.py` with SensibleSolver
- [ ] Create `backend/app/api/process.py` with POST /api/v1/process
- [ ] Register process router in `backend/app/api/router.py`
- [ ] Write tests: `backend/tests/test_sensible_process.py`
  - Sensible heating from 55°F to 75°F at known W, verify Qs
  - Sensible cooling from 75°F to 55°F, verify same magnitude
  - DELTA_T mode: +20°F from 55°F → 75°F
  - HEAT_AND_AIRFLOW mode: known Q + CFM → verify ΔT and end state
  - Edge case: cooling below dew point triggers warning
  - SI unit test

**Verification:** POST a sensible heating process, get back correct end state and energy.

---

### Chunk 2.2 — Cooling & Dehumidification Solver

**Goal:** The most important HVAC process — cooling air below its dew point through a coil.

#### Two Modes

**Forward mode (ADP + BF → leaving state):**
- Input: start state + ADP dry-bulb temperature + bypass factor (0 < BF < 1)
- Resolve ADP as a saturation state: `resolve_state_point(("Tdb", "RH"), (adp_Tdb, 100), pressure, unit_system)`
- Leaving Tdb = ADP_Tdb + BF × (entering_Tdb - ADP_Tdb)
- Leaving W = ADP_W + BF × (entering_W - ADP_W)
- Resolve leaving state from Tdb + W
- CF (contact factor) = 1 - BF

**Reverse mode (entering + leaving → ADP + BF):**
- Input: start state + leaving Tdb + leaving RH (or leaving Twb)
- Resolve leaving state
- ADP = intersection of the line through (entering, leaving) with the saturation curve
  - The process line in Tdb-W space is: W = W_entering + slope × (Tdb - Tdb_entering), where slope = (W_leaving - W_entering) / (Tdb_leaving - Tdb_entering)
  - Find Tdb_adp where `W_sat(Tdb) == W_line(Tdb)` using brentq
  - Search domain: Tdb from the saturation curve minimum up to the leaving Tdb
- BF = (leaving_Tdb - ADP_Tdb) / (entering_Tdb - ADP_Tdb)

**ADP finder implementation:**
```python
def find_adp(entering_Tdb, entering_W, leaving_Tdb, leaving_W, pressure, unit_system):
    """Find the apparatus dew point (intersection of process line with saturation curve)."""
    slope = (leaving_W - entering_W) / (leaving_Tdb - entering_Tdb)

    def objective(Tdb):
        W_on_line = entering_W + slope * (Tdb - entering_Tdb)
        W_sat = psychrolib.GetSatHumRatio(Tdb, pressure)
        return W_sat - W_on_line

    # ADP must be at or below the leaving temperature
    Tdb_min = <chart_min>  # from config ranges
    Tdb_max = leaving_Tdb
    adp_Tdb = brentq(objective, Tdb_min, Tdb_max, xtol=1e-8)
    return adp_Tdb
```

**Edge cases:**
- ADP not found (process line doesn't intersect saturation curve): return error "Process line does not intersect the saturation curve. Check entering and leaving conditions."
- BF < 0 or BF > 1: return error "Computed bypass factor is out of range (0-1). The leaving state may be beyond the ADP."

**Path:** Straight line from entering to leaving (10 intermediate points for chart rendering), plus an optional dashed extension to the ADP for reference.

**Metadata:** `{ADP_Tdb, ADP_W, ADP_W_display, BF, CF, Qs, Ql, Qt, SHR}`

Where:
- Qs = 1.08 × CFM × (Tdb_entering - Tdb_leaving) [IP] — if CFM not provided, report as BTU/lb via enthalpy difference
- Ql = 0.68 × CFM × (W_entering - W_leaving) × 7000 [IP, W in lb/lb] — or from enthalpy
- Qt = 4.5 × CFM × (h_entering - h_leaving) [IP] — or h_entering - h_leaving per lb
- SHR = Qs / Qt

#### Tasks
- [ ] Create `backend/app/engine/processes/cooling_dehum.py`
- [ ] Implement forward mode (ADP + BF → leaving)
- [ ] Implement reverse mode (entering + leaving → ADP + BF)
- [ ] Implement `find_adp()` helper
- [ ] Add `COOLING_DEHUMIDIFICATION` dispatch to process route
- [ ] Write tests: `backend/tests/test_cooling_dehum.py`
  - Classic example: 80°F/67°F wb entering, 55°F/54°F wb leaving → verify ADP, BF, loads
  - Forward mode: known ADP (45°F) + BF (0.15) → verify leaving conditions
  - Reverse mode: same entering/leaving → verify back-calculated ADP matches
  - Round-trip: forward then reverse with same inputs → same ADP/BF
  - Edge case: line doesn't intersect saturation curve
  - SI units

**Verification:** Classic textbook cooling coil problem. Both modes should agree when given consistent data.

---

### Chunk 2.3 — Adiabatic Mixing Solver

**Goal:** Calculate mixed air conditions from two (or more) airstreams.

#### Approach

The mixing calculation is straightforward:
1. Convert CFM to mass flow using specific volume: `m = CFM / v` (IP: lb/min) or `m = airflow / v` (SI: kg/s)
2. Mix by mass-weighted average:
   - `W_mix = (m1 × W1 + m2 × W2) / (m1 + m2)`
   - `h_mix = (m1 × h1 + m2 × h2) / (m1 + m2)`
3. Resolve mixed state from **Tdb + W**: Since we have W_mix, use the existing `Tdb+h` resolver to find Tdb_mix from h_mix and W_mix.

**Corrected resolution approach**: The mixed state has known W_mix and h_mix. To find Tdb_mix:
- Use the enthalpy equation algebraically: `Tdb = (h - W × c2) / (c1 + W × c3)` where c1, c2, c3 are the psychrometric constants. In IP: `Tdb = (h - W × 1061) / (0.240 + W × 0.444)`.
- Then resolve the full state from `(Tdb_mix, W_mix)` using the existing `_resolve_tdb_w()` path.
- Alternatively, use the existing `_resolve_tdb_h()` iterative resolver by passing Tdb as an initial guess and h as target — but this requires Tdb which we don't have yet. The algebraic approach is cleaner.

#### Data Model

New file or addition to `backend/app/models/mixing.py`:

```python
class MixingStreamInput(BaseModel):
    """One airstream in a mixing calculation."""
    input_pair: tuple[str, str]
    values: tuple[float, float]
    airflow: float   # CFM (IP) or m³/s (SI)
    label: str = ""

class MixingInput(BaseModel):
    """Input for adiabatic mixing calculation."""
    streams: list[MixingStreamInput]  # 2 or more streams
    unit_system: UnitSystem = UnitSystem.IP
    pressure: float = DEFAULT_PRESSURE_IP

class MixingOutput(BaseModel):
    """Result of an adiabatic mixing calculation."""
    unit_system: UnitSystem
    pressure: float
    streams: list[dict]           # Each stream's resolved state + mass flow
    mixed_point: dict             # Full StatePointOutput as dict
    path_points: list[PathPoint]  # Line from stream 1 to stream 2 (2-stream case)
    metadata: dict                # {total_airflow, mass_flows, mixing_ratios}
```

#### Edge Cases
- **Two identical streams**: Should work fine, mixed point equals both inputs
- **One stream at 0 CFM**: Effectively no mixing, result equals the other stream. Allow this (don't error).
- **More than 2 streams**: Supported — just extend the mass-weighted average to N streams. Path visualization only shown for 2-stream case.
- **Mixed point above saturation**: If the mixed W_mix exceeds W_sat at Tdb_mix, condensation occurs. Add warning: "Mixed air is supersaturated — condensation would occur."

#### API Route

New file: `backend/app/api/mixing.py`

- `POST /api/v1/mixing` — takes MixingInput, returns MixingOutput
- Register in `router.py`

#### Tasks
- [ ] Create `backend/app/models/mixing.py` with MixingStreamInput, MixingInput, MixingOutput
- [ ] Create `backend/app/engine/processes/mixing.py`
- [ ] Implement 2-stream mixing with algebraic Tdb resolution
- [ ] Extend to N-stream mixing
- [ ] Create `backend/app/api/mixing.py` with POST /api/v1/mixing
- [ ] Register mixing router in `backend/app/api/router.py`
- [ ] Write tests: `backend/tests/test_mixing.py`
  - Standard OA mixing: 80% return air (75°F/50%) + 20% outdoor air (95°F/75°F wb)
  - Verify mixed point lies on the line between the two states
  - Equal flow rates: mixed point at midpoint
  - 3-stream mixing
  - Edge: one stream at 0 CFM
  - SI units

**Verification:** Standard OA mixing problem. Verify mixed point lies on the line between the two states proportionally to mass flow ratios.

---

### Chunk 2.4 — Process UI (Builder, Rendering, List)

**Goal:** Frontend can define, render, and manage processes on the chart.

#### Zustand Store Changes

Update `frontend/src/store/useStore.ts`:

```typescript
// New state
processes: ProcessOutput[]
processLoading: boolean
processError: string | null

// New actions
addProcess: (process: ProcessOutput) => void
removeProcess: (index: number) => void
clearProcesses: () => void
setProcessLoading: (loading: boolean) => void
setProcessError: (error: string | null) => void
```

#### New TypeScript Types

Update `frontend/src/types/psychro.ts`:

```typescript
interface ProcessOutput {
  process_type: string
  unit_system: string
  pressure: number
  start_point: StatePointOutput
  end_point: StatePointOutput
  path_points: {Tdb: number, W: number, W_display: number}[]
  metadata: Record<string, number | string>
  warnings: string[]
}

interface MixingOutput {
  unit_system: string
  pressure: number
  streams: Record<string, any>[]
  mixed_point: StatePointOutput
  path_points: {Tdb: number, W: number, W_display: number}[]
  metadata: Record<string, number | string>
}
```

#### New Components

**`frontend/src/components/Process/ProcessBuilder.tsx`:**
- Process type dropdown (sensible heating, sensible cooling, cooling & dehum, mixing)
- Dynamic form that adapts to selected process:
  - Sensible: start point selector (dropdown of existing state points OR manual input pair) + mode selector (target Tdb / ΔT / Q+CFM) + appropriate inputs
  - Cooling & dehum: start point + mode (forward: ADP + BF / reverse: leaving conditions)
  - Mixing: two stream selectors (existing point OR manual) + CFM for each
- Submit → call backend → store result in Zustand → auto-add end point to state points

**Update `frontend/src/components/Chart/PsychroChart.tsx`:**
- Render process lines as new Plotly traces
- Line styles: solid for process path, dashed for ADP extension
- Color: distinct from background lines (e.g., orange for sensible, cyan for cooling, magenta for mixing)
- Arrow annotations showing process direction (Plotly annotations with `ax`/`ay`)
- Process end points auto-added as state points if not already present

**`frontend/src/components/Process/ProcessList.tsx`:**
- List all processes with type, start/end labels, key metadata summary
- Expandable detail row for full metadata (Qs, Ql, Qt, SHR, BF, etc.)
- Warnings displayed inline (yellow text)
- Delete button per process

#### API Client Additions

Update `frontend/src/api/client.ts`:

```typescript
async function calculateProcess(input: ProcessInput): Promise<ProcessOutput>
async function calculateMixing(input: MixingInput): Promise<MixingOutput>
```

#### Layout Changes

- Add a "Processes" section below the state points in the Sidebar
- Or: add a tab system to the Sidebar (Points | Processes)

#### Tasks
- [ ] Update TypeScript types in `psychro.ts` for ProcessOutput, MixingOutput
- [ ] Update Zustand store with process state slice and actions
- [ ] Add API client functions for process and mixing endpoints
- [ ] Create `ProcessBuilder.tsx` with dynamic forms per process type
- [ ] Create `ProcessList.tsx` with expandable metadata cards
- [ ] Update `PsychroChart.tsx` to render process lines and arrows
- [ ] Update `Sidebar.tsx` to include process builder and list
- [ ] Manual integration test: build a simple AHU chain (OA+RA mix → cooling coil → supply)

**Verification:** Build a simple AHU process chain: OA + RA mix → cooling coil → supply. See all processes on the chart with correct paths and metadata.

---

**PHASE 2 COMPLETE**

At this point we have: the base chart + state points + the three most-used HVAC processes (sensible, cooling/dehum, mixing) fully working with UI.

---

## PHASE 3: Extended Processes

### Chunk 3.1 — Humidification Solvers (Steam, Adiabatic, Heated Water)

**Tasks:**
- Steam humidification solver: constant Tdb (vertical path), given start + target W or RH
- Adiabatic humidification solver: constant Twb (diagonal path toward saturation), given start + effectiveness or target RH
- Heated water spray solver: path between vertical and diagonal depending on water temp, parameterized by water temperature
- Path generation for each (straight or along Twb curve)
- Tests for each

---

### Chunk 3.2 — Evaporative Cooling Solvers (Direct, Indirect, Two-Stage)

**Tasks:**
- Direct evaporative: along constant Twb line, parameterized by effectiveness
- Indirect evaporative: sensible cooling only (horizontal), parameterized by effectiveness and secondary airstream wet-bulb
- Indirect-direct two-stage: two connected segments (horizontal then diagonal)
- Path generation for each
- Tests for each

---

### Chunk 3.3 — Chemical Dehumidification + Sensible Reheat

**Tasks:**
- Chemical/desiccant dehumidification: approximately constant h, Tdb rises as W drops. Given start + target W.
- Sensible reheat: horizontal path (same as sensible heating, but contextually follows a dehumidification step). Given start + target Tdb.
- Tests for each

---

### Chunk 3.4 — Extended Process UI + Process Chaining

**Tasks:**
- Extend `ProcessBuilder.tsx` to support all new process types with appropriate parameter forms
- Implement process chaining: the end point of one process can be selected as the start point of the next
  - UI: "chain from previous" toggle that auto-selects the last process's end point
  - Visual: connected process traces on the chart with sequential numbering/coloring
- Update `ProcessList.tsx` to show chain relationships
- Render all new process paths on chart (curved paths for adiabatic/evaporative)

---

**PHASE 3 COMPLETE**

Full process coverage. Every psychrometric process from the list is implemented and renderable.

---

## PHASE 4: Coil Analysis & SHR Tools

### Chunk 4.1 — Coil Analysis Engine + API

**Tasks:**
- Implement `engine/coil.py`:
  - Forward calc: entering conditions + ADP + BF → leaving conditions + loads
  - Reverse calc: entering + leaving conditions → ADP + BF
  - Full load breakdown: Qs, Ql, Qt, SHR
  - GPM estimate (given entering/leaving water temps and Qt)
- Implement `/api/v1/coil` endpoint
- Tests with known coil data

---

### Chunk 4.2 — SHR Line Engine + API

**Tasks:**
- Implement `engine/shr.py`:
  - Room SHR line: given room state + SHR → compute slope, generate line points through room state
  - ADP from SHR: find intersection of SHR line with saturation curve
  - Grand SHR: given room conditions, OA conditions, OA fraction, room loads → GSHR
  - Effective SHR: given GSHR + BF → ESHR
- Implement `/api/v1/shr` endpoint
- Tests against textbook GSHR/ESHR examples

---

### Chunk 4.3 — Coil & SHR Frontend

**Tasks:**
- `CoilAnalysis.tsx` panel:
  - Input form: entering conditions (select from existing state points or enter manually), leaving conditions or ADP+BF
  - Results display: full load breakdown, ADP, BF, CF
  - Button to add the coil process to the chart
- SHR line rendering on chart:
  - Draw SHR line through selected room point
  - Mark ADP intersection on saturation curve
  - Optional: SHR protractor reference in corner of chart
- Integrate with process chain (coil process links to SHR line)

---

**PHASE 4 COMPLETE**

Full coil analysis and SHR tooling — the stuff that directly feeds into AHU and coil selection.

---

## PHASE 5: Airflow, Energy & Utilities

### Chunk 5.1 — Airflow & Energy Calculation Engine + API

**Tasks:**
- Implement `engine/airflow.py`:
  - Sensible: Qs = C x CFM x delta_T (solve for any variable)
  - Latent: Ql = C x CFM x delta_W (solve for any variable)
  - Total: Qt = C x CFM x delta_h (solve for any variable)
  - Altitude correction factors for the C constants
  - Air density at conditions
  - Condensation check: is_condensing(surface_temp, dew_point) -> bool
- Implement `/api/v1/airflow-calc` endpoint
- Tests at sea level and at altitude (e.g., 5000 ft)

---

### Chunk 5.2 — Utilities Frontend

**Tasks:**
- `AirflowCalc.tsx` panel:
  - Mode selector: solve for Q, CFM, or delta_T/delta_W/delta_h
  - Input fields adapt to selected mode
  - "Auto-fill from process" button: select a process, auto-populate delta values
  - Altitude correction display
  - Condensation risk checker: input surface temp, select a state point -> flag yes/no
- Results display with formula shown

---

**PHASE 5 COMPLETE**

All the quick-calc utilities are in place. The app is now a comprehensive psychrometric design tool.

---

## PHASE 6: Polish & Export

### Chunk 6.1 — Project Save/Load + Data Export

**Tasks:**
- Define JSON schema for project file (all state points, processes, settings)
- Save project -> download .json file
- Load project -> upload .json file -> restore full state
- Export chart as PNG/SVG (Plotly built-in)
- Export data table as CSV

---

### Chunk 6.2 — Chart Interactivity Enhancements

**Tasks:**
- Click on chart to add a state point (opens pre-filled form with clicked Tdb/W)
- Process chain visual builder: click start point -> select process type -> click or configure end -> trace appears
- Keyboard shortcuts (Delete to remove selected point, Ctrl+Z for undo)
- Undo/redo system (state history stack in Zustand)

---

### Chunk 6.3 — UI Polish

**Tasks:**
- Responsive panel layout (resizable sidebar)
- Color theme for process types (consistent legend)
- Chart legend panel (toggle visibility of background lines, processes)
- Light mode option (dark mode is current default)
- Loading states and error handling throughout
- Print-friendly chart layout

---

**PHASE 6 COMPLETE**

The app is polished and production-usable.

---

## PHASE 7: Stretch Goals (pick and choose)

| Chunk | Feature |
|---|---|
| 7.1 | ASHRAE design day conditions overlay (by city/CZ) |
| 7.2 | TMY bin data scatter/heatmap overlay |
| 7.3 | AHU wizard mode (guided workflow) |
| 7.4 | Multi-project comparison (overlay two projects) |
| 7.5 | Electron/Tauri native Windows wrapper |
| 7.6 | PDF report generation |
| 7.7 | CoolProp integration (refrigerant properties) |

---

## Summary: Chunk Count by Phase

| Phase | Chunks | Status |
|---|---|---|
| Phase 1 — Foundation | 5 chunks | ✅ Complete |
| Phase 2 — Core Processes | 4 chunks | 🔲 Up Next |
| Phase 3 — Extended Processes | 4 chunks | 🔲 Planned |
| Phase 4 — Coil & SHR | 3 chunks | 🔲 Planned |
| Phase 5 — Utilities | 2 chunks | 🔲 Planned |
| Phase 6 — Polish | 3 chunks | 🔲 Planned |
| Phase 7 — Stretch | a la carte | 🔲 Backlog |
| **Total (Phases 1-6)** | **21 chunks** | |

---

## Recommended Build Order

Continue sequentially from **Chunk 2.1**. Each chunk is designed so that at the end of it, you can run the app and see/test the new capability. No chunk leaves you in a broken intermediate state.

**Before starting Chunk 2.1:** Confirm the backend starts and all 79 tests pass.

```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Tests
python -m pytest tests/ -v
```
