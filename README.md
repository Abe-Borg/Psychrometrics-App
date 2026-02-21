# PsychroApp

Interactive psychrometric chart application for HVAC design. All thermodynamic calculations are handled programmatically using [psychrolib](https://github.com/psychrometrics/psychrolib) (ASHRAE-backed formulas).

## Status

**Chunk 1.1 — Backend Scaffolding + State Point Engine**: ✅ Complete
**Chunk 1.2 — Chart Background Data Generator**: ✅ Complete
**Chunk 1.3 — Frontend Scaffolding + Base Chart Rendering**: ✅ Complete

### What's Working
- FastAPI backend with psychrolib integration
- State point resolver supporting 7 input pair combinations:
  - `Tdb + RH` (dry-bulb + relative humidity)
  - `Tdb + Twb` (dry-bulb + wet-bulb)
  - `Tdb + Tdp` (dry-bulb + dew point)
  - `Tdb + W` (dry-bulb + humidity ratio)
  - `Tdb + h` (dry-bulb + enthalpy) — iterative solver
  - `Twb + RH` (wet-bulb + relative humidity) — iterative solver
  - `Tdp + RH` (dew point + relative humidity) — iterative solver
- Full property resolution: Tdb, Twb, Tdp, RH, W, W (grains/g·kg⁻¹), h, v, Pv, Ps, μ
- Chart background data generator producing:
  - Saturation curve (200 points)
  - Constant RH lines (10%–90% in 10% steps)
  - Constant wet-bulb lines (12 lines across chart range)
  - Constant enthalpy lines (10 lines across chart range)
  - Constant specific volume lines (6 lines across chart range)
- IP and SI unit system support
- Altitude-to-pressure conversion (chart data adjusts for non-standard pressure)
- Input pair can be given in either order (e.g., `RH, Tdb` works the same as `Tdb, RH`)
- 79 passing tests validating against ASHRAE reference data
- CORS configured for local frontend development
- React + TypeScript + Tailwind frontend with:
  - Interactive Plotly.js psychrometric chart (zoom, pan, scroll-zoom)
  - All background lines rendered: saturation curve, RH, Twb, enthalpy, volume
  - Color-coded line types with legend
  - Unit system toggle (IP ↔ SI) with live chart reload
  - Altitude and pressure inputs with auto-conversion
  - Zustand state management
  - Vite dev server with API proxy to backend

### What's Next
- **Chunk 1.4**: State point UI (input form, display, plot on chart)

## Tech Stack

| Layer | Technology |
|---|---|
| Psychrometric engine | psychrolib 2.5.0 |
| Backend | FastAPI + Python 3.12 |
| Iterative solvers | SciPy (brentq) |
| Validation | Pydantic |
| Frontend | React + TypeScript (Vite) |
| Charting | Plotly.js (react-plotly.js) |
| State management | Zustand |
| Styling | Tailwind CSS v4 |
| Testing | pytest |

## Project Structure

```
psychro-app/
├── README.md
├── requirements.txt
├── venv/                            # created locally
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Constants, defaults, units
│   │   ├── api/
│   │   │   ├── router.py            # Top-level API router
│   │   │   ├── state_point.py       # /state-point routes
│   │   │   └── chart_data.py        # /chart-data routes
│   │   ├── engine/
│   │   │   ├── state_resolver.py    # Core state point calculation
│   │   │   ├── chart_generator.py   # Chart background line generation
│   │   │   └── processes/           # (future) process solvers
│   │   └── models/
│   │       └── state_point.py       # Pydantic models
│   └── tests/
│       ├── test_state_resolver.py   # 50 tests
│       └── test_chart_generator.py  # 29 tests
└── frontend/
    ├── package.json
    ├── vite.config.ts               # Vite + Tailwind + API proxy
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx                 # Entry point
        ├── App.tsx                  # Root component
        ├── app.css                  # Global styles + Tailwind
        ├── api/
        │   └── client.ts           # Backend API client
        ├── store/
        │   └── useStore.ts         # Zustand state management
        ├── types/
        │   └── psychro.ts          # TypeScript interfaces
        ├── utils/
        │   └── formatting.ts       # Display formatting helpers
        └── components/
            ├── Chart/
            │   └── PsychroChart.tsx # Main Plotly chart
            └── Layout/
                ├── AppLayout.tsx    # Top-level layout
                ├── Toolbar.tsx      # Unit/altitude/pressure controls
                └── Sidebar.tsx      # Sidebar (placeholder)
```

## Setup

### Prerequisites
- Python 3.12+

### Backend

```bash
cd psychro-app
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Run the Server

```bash
# From project root with venv activated
set PYTHONPATH=backend        # Windows
export PYTHONPATH=backend     # macOS/Linux

uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Run Tests

```bash
# From project root with venv activated
PYTHONPATH=backend python -m pytest backend/tests/ -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. API calls are proxied to the backend at `http://localhost:8000`.

**Both servers must be running** — start the backend first, then the frontend.

## API Reference

### `POST /api/v1/state-point`

Resolve a full psychrometric state point from two independent properties.

**Request:**
```json
{
  "input_pair": ["Tdb", "RH"],
  "values": [75.0, 50.0],
  "pressure": 14.696,
  "unit_system": "IP",
  "label": "Room"
}
```

**Response:**
```json
{
  "label": "Room",
  "unit_system": "IP",
  "pressure": 14.696,
  "input_pair": ["Tdb", "RH"],
  "input_values": [75.0, 50.0],
  "Tdb": 75.0,
  "Twb": 62.5525,
  "Tdp": 55.1199,
  "RH": 50.0,
  "W": 0.0092357,
  "W_display": 64.6497,
  "h": 28.1066,
  "v": 13.6792,
  "Pv": 0.215037,
  "Ps": 0.430075,
  "mu": 0.492575
}
```

### `GET /api/v1/chart-data`

Generate all psychrometric chart background line data.

**Parameters:**
- `unit_system` (string, optional): `IP` or `SI` (default: `IP`)
- `pressure` (float, optional): Atmospheric pressure; psia for IP, Pa for SI (default: sea level)

**Response (abbreviated):**
```json
{
  "unit_system": "IP",
  "pressure": 14.696,
  "ranges": { "Tdb_min": 20.0, "Tdb_max": 120.0, "W_min": 0.0, "W_max": 220.0 },
  "saturation_curve": [ { "Tdb": 20.0, "W": 0.002144, "W_display": 15.01 }, ... ],
  "rh_lines": {
    "10": [ { "Tdb": ..., "W": ..., "W_display": ... }, ... ],
    "20": [ ... ],
    ...
    "90": [ ... ]
  },
  "twb_lines": { "30": [...], "35": [...], ... "85": [...] },
  "enthalpy_lines": { "10": [...], "15": [...], ... "55": [...] },
  "volume_lines": { "12.5": [...], "13.0": [...], ... "15.0": [...] }
}
```

Each line is an array of `{Tdb, W, W_display}` points. `W` is in lb/lb (IP) or kg/kg (SI). `W_display` is in grains/lb (IP) or g/kg (SI).

### `GET /api/v1/pressure-from-altitude`

Convert altitude to atmospheric pressure.

**Parameters:**
- `altitude` (float): Altitude in feet (IP) or meters (SI)
- `unit_system` (string, optional): `IP` or `SI` (default: `IP`)

**Response:**
```json
{
  "altitude": 5280.0,
  "pressure": 12.100245,
  "unit_system": "IP"
}
```

### `GET /health`

Health check endpoint.

## Supported Input Pairs

| Pair | Method |
|---|---|
| Tdb + RH | Direct (psychrolib) |
| Tdb + Twb | Direct (psychrolib) |
| Tdb + Tdp | Direct (psychrolib) |
| Tdb + W | Direct (psychrolib) |
| Tdb + h | Iterative (scipy brentq) |
| Twb + RH | Iterative (scipy brentq) |
| Tdp + RH | Iterative (scipy brentq) |

All pairs can be provided in either order.
