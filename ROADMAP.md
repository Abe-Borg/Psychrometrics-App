# PsychroApp — Psychrometric Chart Application

## Roadmap & Architecture

---

## Current Status

| Phase | Status | Notes |
|---|---|---|
| **Phase 1 — Foundation** | ✅ Complete | State points, chart, hover tooltip, full UI |
| **Phase 2 — Core Processes** | 🔲 Up Next | Process solvers + process UI |
| Phase 3 — Extended Processes | 🔲 Planned | Humidification, evaporative, desiccant |
| Phase 4 — Coil & SHR | 🔲 Planned | Coil analysis, SHR/GSHR/ESHR |
| Phase 5 — Utilities | 🔲 Planned | Airflow calcs, energy, condensation |
| Phase 6 — Polish | 🔲 Planned | Save/load, export, interactivity |
| Phase 7 — Stretch | 🔲 Backlog | ASHRAE design days, bin data, etc. |

---

## 1. Vision

A fully interactive, programmable psychrometric chart tool for HVAC designers. All thermodynamic math is handled by proven open-source libraries — no AI approximations, no lookup tables. The user defines state points, traces processes, and gets accurate engineering data back, all rendered on a professional-quality chart.

---

## 2. Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| **Psychrometric engine (backend)** | `psychrolib` (Python) | ASHRAE-backed formulas, lightweight, well-tested, supports IP and SI units |
| **Psychrometric engine (hover)** | `psychrolib` (JS) | Client-side hover tooltip calculations — no API round-trip for cursor tracking |
| **Backend** | FastAPI (Python) | Lightweight async API server, easy to pair with psychrolib |
| **Frontend** | React + TypeScript | Component-based UI, strong ecosystem |
| **Charting** | Plotly.js | Interactive (zoom, pan, hover tooltips), handles custom coordinate systems |
| **State management** | Zustand | Lightweight, sufficient for this scale |
| **Styling** | Tailwind CSS v4 | Fast, utility-first, keeps the UI clean |
| **Build tooling** | Vite | Fast dev server, simple config |
| **Testing** | pytest (backend) | Vitest planned for frontend in later phases |

### Why not fully client-side?

psychrolib has a JS port, but keeping the engine in Python gives us:

- Easier integration with CoolProp later if we want refrigerant calcs
- Ability to do heavier batch calculations (bin data, coil modeling) server-side
- Clean separation: the frontend is purely a rendering/interaction layer

The JS port is used *only* for the real-time hover tooltip. All "real" calculations go through Python.

### Why not Streamlit?

Streamlit limits UI control. A custom React frontend gives full control over chart interactions (click to place points, drag processes, hover data, etc.).

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                     │
│                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Chart Panel  │  │ Input Panel  │  │ Data Table  │  │
│  │ (Plotly.js)  │  │ (forms/ctrls)│  │ (results)   │  │
│  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│         │                 │                │         │
│         └─────────┬───────┘────────────────┘         │
│                   │                                  │
│            State Management (Zustand)                │
│                   │                                  │
└───────────────────┼──────────────────────────────────┘
                    │  HTTP / JSON
┌───────────────────┼──────────────────────────────────┐
│                   │     FastAPI Backend               │
│                   ▼                                   │
│  ┌──────────────────────────────────┐                │
│  │        API Router Layer          │                │
│  │  /state-point    ✅              │                │
│  │  /chart-data     ✅              │                │
│  │  /process        (Phase 2)       │                │
│  │  /mixing         (Phase 2)       │                │
│  │  /coil           (Phase 4)       │                │
│  └──────────────┬───────────────────┘                │
│                 │                                     │
│  ┌──────────────▼───────────────────┐                │
│  │      Calculation Engine          │                │
│  │                                  │                │
│  │  ┌────────────┐ ┌─────────────┐  │                │
│  │  │ psychrolib │ │  Process    │  │                │
│  │  │ (props) ✅ │ │  Solvers    │  │                │
│  │  └────────────┘ └─────────────┘  │                │
│  │  ┌────────────┐ ┌─────────────┐  │                │
│  │  │ Coil Model │ │  Utilities  │  │                │
│  │  │            │ │  (SHR, BF)  │  │                │
│  │  └────────────┘ └─────────────┘  │                │
│  └──────────────────────────────────┘                │
└──────────────────────────────────────────────────────┘
```

---

## 4. Data Model

### 4.1 State Point ✅ Implemented

The fundamental unit. Every point on the chart is fully defined by two independent properties plus atmospheric pressure.

```python
class StatePointOutput:
    label: str
    unit_system: str           # "IP" or "SI"
    pressure: float            # barometric pressure (psia or Pa)
    input_pair: tuple[str, str]
    input_values: tuple[float, float]

    # Resolved properties (calculated)
    Tdb: float                 # dry-bulb temperature (°F or °C)
    Twb: float                 # wet-bulb temperature
    Tdp: float                 # dew point temperature
    RH: float                  # relative humidity (0-100%)
    W: float                   # humidity ratio (lb_w/lb_da or kg_w/kg_da)
    W_display: float           # humidity ratio for display (grains/lb or g/kg)
    h: float                   # specific enthalpy (BTU/lb or kJ/kg)
    v: float                   # specific volume (ft³/lb or m³/kg)
    Pv: float                  # partial vapor pressure
    Ps: float                  # saturation pressure at Tdb
    mu: float                  # degree of saturation
```

### 4.2 Process (Phase 2)

A transformation from one state point to another, with a defined path type.

```python
class ProcessResult:
    process_type: ProcessType
    start_point: StatePointOutput
    end_point: StatePointOutput
    path_points: list[dict]           # [{Tdb, W, W_display}, ...] for chart rendering
    metadata: dict                     # process-specific data (BF, ADP, SHR, loads, etc.)

class ProcessType(Enum):
    # Phase 2
    SENSIBLE_HEATING = "sensible_heating"
    SENSIBLE_COOLING = "sensible_cooling"
    COOLING_DEHUMIDIFICATION = "cooling_dehumidification"
    ADIABATIC_MIXING = "adiabatic_mixing"

    # Phase 3
    HEATING_HUMIDIFICATION_STEAM = "heating_humidification_steam"
    HEATING_HUMIDIFICATION_ADIABATIC = "heating_humidification_adiabatic"
    HEATING_HUMIDIFICATION_HEATED_WATER = "heating_humidification_heated_water"
    CHEMICAL_DEHUMIDIFICATION = "chemical_dehumidification"
    DIRECT_EVAPORATIVE_COOLING = "direct_evaporative_cooling"
    INDIRECT_EVAPORATIVE_COOLING = "indirect_evaporative_cooling"
    INDIRECT_DIRECT_EVAPORATIVE = "indirect_direct_evaporative"
    SENSIBLE_REHEAT = "sensible_reheat"

    # Phase 4
    SHR_LINE = "shr_line"
```

### 4.3 Project / Session (Phase 6)

```python
class PsychroProject:
    id: str
    name: str
    unit_system: "IP" | "SI"
    altitude: float
    pressure: float
    state_points: list[StatePoint]
    processes: list[Process]
    notes: str
```

---

## 5. API Endpoints

### Implemented

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/state-point` | POST | Resolve full state point from 2 properties |
| `/api/v1/chart-data` | GET | All chart background line data |
| `/api/v1/pressure-from-altitude` | GET | Convert altitude to pressure |
| `/health` | GET | Health check |

### Planned

| Endpoint | Method | Phase | Description |
|---|---|---|---|
| `/api/v1/process` | POST | 2 | Calculate psychrometric process |
| `/api/v1/mixing` | POST | 2 | Adiabatic mixing of airstreams |
| `/api/v1/coil` | POST | 4 | Coil analysis (ADP, BF, loads) |
| `/api/v1/shr` | POST | 4 | SHR line and GSHR/ESHR |
| `/api/v1/airflow-calc` | POST | 5 | Airflow/energy utilities |

---

## 6. Calculation Engine Details

### 6.1 State Point Resolver ✅ Implemented

Supported input pairs:
- Tdb + RH — direct (psychrolib)
- Tdb + Twb — direct (psychrolib)
- Tdb + Tdp — direct (psychrolib)
- Tdb + W — direct (psychrolib)
- Tdb + h — iterative (scipy brentq)
- Twb + RH — iterative (scipy brentq)
- Tdp + RH — iterative (scipy brentq)

All pairs can be provided in either order.

**Implementation notes:**
- psychrolib requires `SetUnitSystem()` before every call
- psychrolib returns RH as 0-1; we multiply by 100 for display
- W is converted to grains (x7000) or g/kg (x1000) for `W_display`
- Dispatch table maps input pairs to resolver functions, handles reverse order

### 6.2 Process Solvers (Phase 2+)

Each process type gets its own solver. Takes start state + parameters, returns end state + path points + metadata.

### 6.3 Altitude / Pressure ✅ Implemented

psychrolib takes atmospheric pressure as an input to every function. Altitude-to-pressure conversion uses psychrolib's `GetStandardAtmPressure()`.

---

## 7. Development Phases

### Phase 1 — Foundation ✅ COMPLETE

- [x] Backend scaffolding, state point resolver (7 input pairs), chart data generator
- [x] 79 passing tests
- [x] React + Plotly.js interactive chart with all background lines
- [x] State point UI (form, list, chart markers)
- [x] Live hover tooltip (client-side psychrolib.js)
- [x] Unit system toggle, altitude/pressure controls

### Phase 2 — Core Processes (Up Next)

- [ ] Process solver framework + sensible heating/cooling
- [ ] Cooling & dehumidification (ADP, BF)
- [ ] Adiabatic mixing (2-stream)
- [ ] Process UI (builder, chart rendering, list)

### Phase 3 — Extended Processes

- [ ] Steam, adiabatic, heated water humidification
- [ ] Direct, indirect, 2-stage evaporative cooling
- [ ] Chemical dehumidification, sensible reheat
- [ ] Process chaining UI

### Phase 4 — Coil Analysis & SHR Tools

- [ ] Coil analysis (forward and reverse)
- [ ] SHR line, Grand SHR, Effective SHR
- [ ] Coil & SHR frontend

### Phase 5 — Airflow, Energy & Utilities

- [ ] Qs/Ql/Qt calculations with altitude corrections
- [ ] Solve-for-any-variable
- [ ] Condensation risk check
- [ ] Utilities frontend

### Phase 6 — Polish, UX, Export

- [ ] Project save/load (JSON)
- [ ] Chart/data export (PNG, SVG, CSV)
- [ ] Click-to-add points, drag, keyboard shortcuts
- [ ] Undo/redo, responsive layout

### Phase 7 — Stretch Goals

- [ ] ASHRAE design day overlay, TMY bin data, CoolProp, AHU wizard, Electron/Tauri wrapper, PDF reports

---

## 8. Design Decisions (Confirmed)

1. **Unit system default**: IP with SI toggle ✅
2. **Humidity ratio display**: grains/lb on chart Y-axis (IP), g/kg (SI) ✅
3. **Chart orientation**: Standard ASHRAE-style (Tdb on X, W on Y) ✅
4. **Altitude default**: Sea level (14.696 psia) ✅
5. **Process path resolution**: 50-100 intermediate points (TBD in Phase 2)
6. **Save format**: JSON (Phase 6)
7. **Deployment**: Local Windows machine

---

## 9. Current File Structure

```
Psychrometrics-App/
├── README.md
├── ROADMAP.md                       # This file
├── IMPLEMENTATION_PLAN.md           # Chunk-by-chunk build plan
├── requirements.txt
├── run_backend.py                   # Backend launcher
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI entry + CORS
│   │   ├── config.py                # UnitSystem, constants, ranges
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Top-level router
│   │   │   ├── state_point.py       # /state-point, /pressure-from-altitude
│   │   │   └── chart_data.py        # /chart-data
│   │   ├── engine/
│   │   │   ├── __init__.py
│   │   │   ├── state_resolver.py    # 7 input pairs
│   │   │   ├── chart_generator.py   # Background lines
│   │   │   └── processes/
│   │   │       └── __init__.py      # Empty — Phase 2
│   │   └── models/
│   │       ├── __init__.py
│   │       └── state_point.py       # Pydantic models
│   └── tests/
│       ├── __init__.py
│       ├── test_state_resolver.py   # 50 tests
│       └── test_chart_generator.py  # 29 tests
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx, App.tsx, app.css
        ├── api/client.ts
        ├── store/useStore.ts
        ├── types/psychro.ts, psychrolib.d.ts
        ├── utils/formatting.ts, hoverCalc.ts
        └── components/
            ├── Chart/PsychroChart.tsx
            ├── StatePoint/StatePointForm.tsx, StatePointList.tsx
            └── Layout/AppLayout.tsx, Toolbar.tsx, Sidebar.tsx
```

---

## 10. Open Questions / Future Considerations

- "Wizard" mode for common HVAC workflows (AHU sizing, etc.)
- Overlaying multiple projects/scenarios on the same chart
- Weather data API integration for ASHRAE design conditions
- Audit trail (log of calculations with formulas shown)

---

*Updated after Phase 1 completion. Next update after Phase 2.*
