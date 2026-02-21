# PsychroApp

Interactive psychrometric chart application for HVAC design. All thermodynamic calculations are handled programmatically using [psychrolib](https://github.com/psychrometrics/psychrolib) (ASHRAE-backed formulas).

## Status

**Chunk 1.1 — Backend Scaffolding + State Point Engine**: ✅ Complete

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
- IP and SI unit system support
- Altitude-to-pressure conversion
- Input pair can be given in either order (e.g., `RH, Tdb` works the same as `Tdb, RH`)
- 50 passing tests validating against ASHRAE reference data
- CORS configured for local frontend development

### What's Next
- **Chunk 1.2**: Chart background data generator (saturation curve, constant RH/Twb/h/v lines)
- **Chunk 1.3**: Frontend scaffolding + base chart rendering (React + Plotly.js)

## Tech Stack

| Layer | Technology |
|---|---|
| Psychrometric engine | psychrolib 2.5.0 |
| Backend | FastAPI + Python 3.12 |
| Iterative solvers | SciPy (brentq) |
| Validation | Pydantic |
| Testing | pytest |

## Project Structure

```
psychro-app/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── config.py                # Constants, defaults, units
│   │   ├── api/
│   │   │   ├── router.py            # Top-level API router
│   │   │   └── state_point.py       # /state-point routes
│   │   ├── engine/
│   │   │   ├── state_resolver.py    # Core state point calculation
│   │   │   └── processes/           # (future) process solvers
│   │   └── models/
│   │       └── state_point.py       # Pydantic models
│   ├── tests/
│   │   └── test_state_resolver.py   # 50 tests
│   ├── requirements.txt
│   └── venv/
└── README.md
```

## Setup

### Prerequisites
- Python 3.12+

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### Run the Server

```bash
cd backend
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

Server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Run Tests

```bash
cd backend
PYTHONPATH=. python -m pytest tests/ -v
```

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
