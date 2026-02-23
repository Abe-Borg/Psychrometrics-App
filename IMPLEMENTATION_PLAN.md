# PsychroApp — Weather Data Analysis & Design Condition Extraction

## Implementation Plan

---

## 1. Purpose and Context

### 1.1 What This Feature Does

This feature allows an HVAC mechanical designer to upload a TMY3/EPW weather data file for a specific geographic location, and have the software automatically extract a small set of **design condition points** (typically 5–8 points) that collectively represent the full range of outdoor conditions the designer's HVAC system must handle across an entire year.

### 1.2 Why This Matters

Today, most mechanical designers size HVAC systems using one or two "peak" design conditions published by ASHRAE (e.g., the 0.4% cooling design temperature). This approach catches the extremes but misses problematic intermediate conditions — for example, a moderately warm but very humid day where the system barely runs in cooling mode but needs to actively dehumidify. Systems designed only for peak conditions can fail to maintain comfort or code-required conditions during these intermediate periods.

This feature solves that by analyzing all 8,760 hours of weather data in a year and extracting:

- **Extreme design points** — the peak cooling, peak heating, and peak dehumidification conditions
- **Intermediate cluster points** — representative conditions for the major "operating regimes" the system will spend most of the year in

The designer can then check their proposed system against each of these points (manually or with future tooling) and be confident the system works year-round — not just on the single hottest or coldest day.

### 1.3 What the Output Looks Like (Conceptually)

After processing a weather file, the user sees:

1. **A psychrometric chart** with all 8,760 hourly data points plotted, color-coded by cluster membership
2. **Highlighted design points** — larger, distinctly styled markers for each extracted design condition
3. **A summary table** listing each design point with its full psychrometric properties (dry-bulb, wet-bulb, dewpoint, humidity ratio, enthalpy, relative humidity, specific volume)
4. **Cluster metadata** — how many hours fall in each cluster (tells the designer what fraction of the year the system operates in that regime)

Example output for an inland Southern California location:

| Point | Type | DB (°F) | WB (°F) | DP (°F) | ω (gr/lb) | h (BTU/lb) | Hours |
|-------|------|---------|---------|---------|-----------|------------|-------|
| 1 | Peak Cooling | 104.2 | 71.1 | 58.3 | 73.2 | 37.8 | — |
| 2 | Peak Heating | 33.8 | 32.1 | 29.5 | 25.8 | 11.2 | — |
| 3 | Peak Dehum. | 76.5 | 67.2 | 63.1 | 92.4 | 31.5 | — |
| 4 | Cluster A (warm dry) | 88.3 | 64.2 | 49.7 | 54.1 | 32.1 | 1,740 |
| 5 | Cluster B (mild) | 71.8 | 58.4 | 49.2 | 53.5 | 25.8 | 2,350 |
| 6 | Cluster C (cool) | 53.1 | 47.8 | 42.1 | 37.8 | 18.2 | 1,680 |
| 7 | Cluster D (warm humid) | 78.4 | 65.1 | 59.8 | 80.3 | 30.4 | 890 |

---

## 2. Architecture Overview

### 2.1 Module Structure

This feature is composed of four distinct modules, each with a clear responsibility:

```
weather_analysis/
├── __init__.py
├── epw_parser.py          # Reads and validates EPW files
├── psychrometric_calc.py  # Computes full psychrometric state from partial inputs
├── clustering.py          # Performs k-means clustering and extracts design points
└── design_extractor.py    # Orchestrates the full pipeline: parse → compute → cluster → extract
```

Additionally, there will be:

- **Backend API endpoints** to accept file uploads and return results
- **Frontend components** to handle file upload, display the chart overlay, and show the summary table

### 2.2 Data Flow

```
EPW File (uploaded by user)
    │
    ▼
epw_parser.py
    │  Extracts hourly records: dry-bulb, dewpoint, atmospheric pressure,
    │  plus metadata (location name, latitude, longitude, elevation, timezone)
    │
    ▼
psychrometric_calc.py
    │  For each hourly record, computes the full psychrometric state:
    │  DB, WB, DP, humidity ratio, enthalpy, RH, specific volume
    │
    ▼
clustering.py
    │  Takes the 8,760 fully-resolved psychrometric states
    │  Runs k-means clustering on (DB, humidity ratio) axes
    │  Returns cluster assignments, centroids, and per-cluster metadata
    │
    ▼
design_extractor.py
    │  Extracts extreme design points (peak cooling, heating, dehumidification)
    │  Extracts representative and worst-case points from each cluster
    │  Packages everything into a structured result object
    │
    ▼
API Response → Frontend
    │  All 8,760 points with cluster labels (for chart plotting)
    │  Design points with full psychrometric properties (for table and chart highlights)
    │  Cluster metadata: hour counts, centroid values
```

### 2.3 Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Psychrometric calculations | **psychrolib** (Python) | Industry-standard library implementing ASHRAE psychrometric formulas. Already used in the existing PsychroApp backend. |
| Clustering | **scikit-learn KMeans** | Well-tested, fast, and appropriate for this use case. pip install scikit-learn. |
| Numerical operations | **NumPy** | Required by scikit-learn anyway; useful for percentile calculations and array operations. |
| Backend framework | **FastAPI** | Already used by PsychroApp. |
| Frontend charting | **Plotly.js** | Already used by PsychroApp for the psychrometric chart. Weather data will be added as additional traces. |

---

## 3. Module Specifications

### 3.1 EPW Parser (`epw_parser.py`)

#### 3.1.1 EPW File Format

An EPW (EnergyPlus Weather) file is a text file with the following structure:

- **Lines 1–8**: Header lines containing metadata. Each header line starts with a keyword, and fields are comma-separated.
  - Line 1 starts with `LOCATION` and contains: city name, state/province, country, data source, WMO station number, latitude, longitude, timezone offset (hours from GMT), and elevation (meters).
  - Lines 2–8 contain other metadata (design conditions, typical periods, ground temperatures, etc.) that we can skip for this implementation.
- **Lines 9 onward**: One line per hour, 8,760 lines total (non-leap year), comma-separated values.

The relevant columns in the hourly data rows (0-indexed) are:

| Column Index | Field | Units in EPW |
|-------------|-------|-------------|
| 0 | Year | integer |
| 1 | Month | 1–12 |
| 2 | Day | 1–31 |
| 3 | Hour | 1–24 (hour ending; hour 1 = 00:00–01:00) |
| 6 | Dry-bulb temperature | °C |
| 7 | Dewpoint temperature | °C |
| 8 | Relative humidity | % (0–100) |
| 9 | Atmospheric pressure | Pa |

**Important**: EPW files store temperatures in Celsius and pressure in Pascals, regardless of the building location. The parser must handle unit conversions downstream or flag the raw units clearly.

#### 3.1.2 Parser Requirements

**Function signature:**

```python
def parse_epw(file_path: str) -> EPWData:
```

**EPWData structure** (use a dataclass or Pydantic model):

```python
@dataclass
class EPWLocation:
    city: str
    state: str
    country: str
    latitude: float     # decimal degrees, positive = North
    longitude: float    # decimal degrees, positive = East
    timezone: float     # hours offset from GMT
    elevation: float    # meters above sea level

@dataclass
class HourlyRecord:
    year: int
    month: int
    day: int
    hour: int           # 1–24
    dry_bulb_c: float   # °C
    dewpoint_c: float   # °C
    rh_percent: float   # 0–100
    pressure_pa: float  # Pascals

@dataclass
class EPWData:
    location: EPWLocation
    hourly_records: list[HourlyRecord]  # length should be 8,760
```

**Validation requirements:**

- Verify the file has at least 8 header lines + data rows
- Verify the first line starts with `LOCATION`
- Verify exactly 8,760 data rows are present (warn if fewer or more)
- Verify numeric fields are valid numbers (not missing or corrupted)
- Handle the common case where some EPW files have 8,784 rows (leap year) — truncate to 8,760 or handle gracefully
- Raise clear, descriptive errors if the file is malformed

**Edge cases:**

- Some EPW files use `99` or `999` or `9999` as missing data indicators. Flag or handle these.
- Atmospheric pressure may be 0 in some files; default to standard atmospheric pressure (101325 Pa) if missing.

#### 3.1.3 Notes on EPW Sources

The user will typically download EPW files from energyplus.net/weather or similar sources. The files are plain text and typically 1.5–2.5 MB in size.

---

### 3.2 Psychrometric Calculator (`psychrometric_calc.py`)

#### 3.2.1 Purpose

For each of the 8,760 hourly records, compute the **full psychrometric state** from the available inputs (dry-bulb, dewpoint, and atmospheric pressure). The outputs are the properties a mechanical designer needs for system sizing.

#### 3.2.2 Using psychrolib

psychrolib is the calculation engine. It must be configured for the correct unit system. The library supports both SI and IP (inch-pound / imperial) units via a global setting:

```python
import psychrolib
psychrolib.SetUnitSystem(psychrolib.SI)  # or psychrolib.IP
```

**Critical**: Set the unit system once at module initialization. All inputs and outputs must match the selected unit system. Since EPW data arrives in SI (°C, Pa), it's simplest to compute in SI first and then convert to IP for display if the user's preference is imperial.

#### 3.2.3 Calculations Per Hour

Given: `dry_bulb_c`, `dewpoint_c`, `pressure_pa`

Compute the following using psychrolib:

```python
# Humidity ratio from dewpoint
humidity_ratio = psychrolib.GetHumRatioFromTDewPoint(dewpoint_c, pressure_pa)
# Returns: kg_water / kg_dry_air (SI) or lb_water / lb_dry_air (IP)

# Wet-bulb temperature
wet_bulb_c = psychrolib.GetTWetBulbFromTDewPoint(dry_bulb_c, dewpoint_c, pressure_pa)

# Relative humidity (as a decimal 0.0–1.0 in psychrolib)
rh = psychrolib.GetRelHumFromTDewPoint(dry_bulb_c, dewpoint_c)
# Note: psychrolib returns RH as a fraction (0.0 to 1.0), not a percentage

# Enthalpy
enthalpy = psychrolib.GetMoistAirEnthalpy(dry_bulb_c, humidity_ratio)
# Returns: J/kg (SI) or BTU/lb (IP)

# Specific volume
specific_volume = psychrolib.GetMoistAirVolume(dry_bulb_c, humidity_ratio, pressure_pa)
# Returns: m³/kg (SI) or ft³/lb (IP)
```

#### 3.2.4 Output Structure

```python
@dataclass
class PsychrometricState:
    # Identifiers
    month: int
    day: int
    hour: int

    # Properties (stored in SI internally; convert on output)
    dry_bulb_c: float
    wet_bulb_c: float
    dewpoint_c: float
    humidity_ratio: float       # kg/kg (SI)
    relative_humidity: float    # fraction 0.0–1.0
    enthalpy_j_per_kg: float   # J/kg (SI)
    specific_volume_m3_per_kg: float  # m³/kg (SI)
    pressure_pa: float

    # For IP display conversions:
    # DB °F = DB °C × 9/5 + 32
    # WB °F = WB °C × 9/5 + 32
    # DP °F = DP °C × 9/5 + 32
    # ω grains/lb = ω kg/kg × 7000
    # h BTU/lb = h J/kg × 0.000429923 (or use psychrolib in IP mode)
    # v ft³/lb = v m³/kg × specific_volume conversion
```

**Important implementation note on unit conversions**: Rather than manually converting between SI and IP, a cleaner approach is to run all psychrolib calculations twice — once in SI for internal clustering math, and once in IP for user-facing output — or to compute everything in SI and convert the final output values. The conversion factors are:

| Property | SI Unit | IP Unit | Conversion |
|----------|---------|---------|-----------|
| Temperature | °C | °F | °F = °C × 9/5 + 32 |
| Humidity ratio | kg/kg | grains/lb | gr/lb = kg/kg × 7000 |
| Enthalpy | J/kg | BTU/lb | BTU/lb = J/kg / 2326 |
| Specific volume | m³/kg | ft³/lb | ft³/lb = m³/kg × 16.018 |
| Pressure | Pa | psi | psi = Pa / 6894.76 |

However, for maximum accuracy, the recommended approach is to use psychrolib in IP mode directly with converted temperature and pressure inputs, rather than converting outputs. psychrolib internally adjusts calculation constants for each unit system.

#### 3.2.5 Batch Processing

Process all 8,760 records and return a list of `PsychrometricState` objects. If any individual record fails calculation (e.g., due to corrupt data), log a warning and skip that hour rather than failing the entire batch.

---

### 3.3 Clustering (`clustering.py`)

#### 3.3.1 Purpose

Group the 8,760 hourly psychrometric states into a manageable number of clusters, each representing a distinct "operating regime" for the HVAC system. Then extract representative and worst-case points from each cluster.

#### 3.3.2 Feature Selection and Normalization

**Clustering axes**: Dry-bulb temperature and humidity ratio. These two properties define a unique point on the psychrometric chart and together capture both sensible and latent conditions.

**Why normalization is critical**: Dry-bulb temperature (in °C) ranges roughly from -10 to 45 for most climates, while humidity ratio (in kg/kg) ranges from about 0.001 to 0.025. Without normalization, temperature would dominate the distance metric and humidity ratio would be effectively ignored.

**Normalization method**: Use StandardScaler from scikit-learn, which transforms each feature to have zero mean and unit variance.

```python
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import numpy as np

# Prepare feature matrix: shape (8760, 2)
X = np.array([[state.dry_bulb_c, state.humidity_ratio] for state in states])

# Normalize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
```

#### 3.3.3 K-Means Configuration

```python
# Default number of clusters
DEFAULT_K = 5

def cluster_weather_data(
    states: list[PsychrometricState],
    n_clusters: int = DEFAULT_K,
    random_state: int = 42  # for reproducibility
) -> ClusterResult:

    X = np.array([[s.dry_bulb_c, s.humidity_ratio] for s in states])
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,      # number of initializations to avoid poor convergence
        max_iter=300     # default, but being explicit
    )
    kmeans.fit(X_scaled)

    labels = kmeans.labels_  # array of length 8760, values 0 to n_clusters-1
    # ...
```

**Why k=5 as default**: For most climates, 5 clusters captures the major operating regimes well (hot-dry, warm-mild, cool, cold, and warm-humid if applicable). The user should be able to adjust this, but 5 is a good starting point.

**Optional enhancement — automatic k selection**: You could implement the elbow method or silhouette score to suggest an optimal k, but this is not required for the initial implementation. A fixed default of 5 with user override is sufficient.

#### 3.3.4 Cluster Analysis Output

For each cluster, extract:

1. **Centroid** (in original, non-scaled coordinates): This is the "typical" condition for that cluster.

   ```python
   # Transform centroids back to original scale
   centroids_original = scaler.inverse_transform(kmeans.cluster_centers_)
   ```

2. **Hour count**: How many of the 8,760 hours belong to this cluster.

3. **Worst-case point**: The hour within this cluster that has the highest moist air enthalpy. This represents the most demanding condition within that operating regime.

   ```python
   # For each cluster, find the point with highest enthalpy
   for cluster_id in range(n_clusters):
       mask = labels == cluster_id
       cluster_states = [s for s, m in zip(states, mask) if m]
       worst = max(cluster_states, key=lambda s: s.enthalpy_j_per_kg)
   ```

4. **Centroid psychrometric state**: The centroid gives you a (DB, ω) pair. From this, compute the full psychrometric state using a representative atmospheric pressure (e.g., the mean pressure from the weather file or the site elevation-adjusted standard pressure).

#### 3.3.5 Output Structure

```python
@dataclass
class ClusterInfo:
    cluster_id: int
    hour_count: int
    centroid_state: PsychrometricState  # full psych state at centroid
    worst_case_state: PsychrometricState  # the actual hour with highest enthalpy in this cluster
    fraction_of_year: float  # hour_count / 8760

@dataclass
class ClusterResult:
    cluster_infos: list[ClusterInfo]
    labels: list[int]  # length 8760, cluster assignment per hour
    all_states: list[PsychrometricState]  # all 8760 states, for plotting
```

---

### 3.4 Design Point Extractor (`design_extractor.py`)

#### 3.4.1 Purpose

This is the orchestration module. It calls the parser, calculator, and clustering modules, then extracts the final set of design points that the designer uses.

#### 3.4.2 Extreme Point Extraction

Three extreme design points, extracted from the full 8,760-hour dataset:

**Peak Cooling Point**:
- Select the hour with the **highest moist air enthalpy**.
- Rationale: Enthalpy captures the total energy content of the air (sensible + latent). The hour with the highest enthalpy is the hour that demands the most from a cooling coil — it must remove the most total energy. This is more accurate than selecting by dry-bulb alone, which misses latent load.

**Peak Heating Point**:
- Select the hour with the **lowest dry-bulb temperature**.
- Rationale: Heating load is almost entirely sensible (driven by temperature difference). Humidity is not a major factor in heating sizing. Using the absolute minimum is appropriate; if you want to be less conservative, use the 0.4th percentile (approximately the 35th lowest hour out of 8,760).
- Implementation: `sorted_by_db = sorted(states, key=lambda s: s.dry_bulb_c)` → take the first element, or use `np.percentile` on the dry-bulb array at 0.4%.

**Peak Dehumidification Point**:
- Select the hour with the **highest dewpoint temperature** (or equivalently, highest humidity ratio) that occurs when dry-bulb is **below the cooling design dry-bulb**.
- Rationale: This captures the condition where the air is very humid but not extremely hot — meaning the cooling system may not run aggressively enough to dehumidify. This is the condition that causes mold, comfort complaints, and code violations in healthcare and education spaces.
- Implementation:
  ```python
  # Find the peak cooling dry-bulb first
  peak_cooling_db = peak_cooling_state.dry_bulb_c
  # Filter to hours below that
  moderate_hours = [s for s in states if s.dry_bulb_c < peak_cooling_db * 0.85]
  # From those, find the one with highest humidity ratio
  peak_dehum = max(moderate_hours, key=lambda s: s.humidity_ratio)
  ```
  The `0.85` factor (85% of peak DB) is a reasonable threshold to isolate "moderate temperature" hours. This can be adjusted; the key is to exclude the truly hot hours where the system is running at full capacity and dehumidifying adequately as a byproduct.

#### 3.4.3 Full Pipeline

```python
def extract_design_conditions(
    epw_file_path: str,
    n_clusters: int = 5,
    unit_system: str = "IP"  # or "SI"
) -> DesignConditionResult:

    # Step 1: Parse
    epw_data = parse_epw(epw_file_path)

    # Step 2: Compute psychrometric states
    states = compute_all_states(epw_data.hourly_records)

    # Step 3: Extract extremes
    peak_cooling = extract_peak_cooling(states)
    peak_heating = extract_peak_heating(states)
    peak_dehum = extract_peak_dehumidification(states, peak_cooling)

    # Step 4: Cluster and extract intermediate points
    cluster_result = cluster_weather_data(states, n_clusters=n_clusters)

    # Step 5: Package results
    design_points = [peak_cooling, peak_heating, peak_dehum]
    for cluster_info in cluster_result.cluster_infos:
        design_points.append(cluster_info.worst_case_state)

    # Step 6: Convert to requested unit system if needed
    if unit_system == "IP":
        design_points = [convert_to_ip(p) for p in design_points]
        # also convert all_states for plotting

    return DesignConditionResult(
        location=epw_data.location,
        design_points=design_points,
        cluster_infos=cluster_result.cluster_infos,
        all_hourly_states=cluster_result.all_states,
        labels=cluster_result.labels
    )
```

#### 3.4.4 Final Output Structure

```python
@dataclass
class DesignPoint:
    label: str                    # e.g., "Peak Cooling", "Cluster 3 Worst-Case"
    point_type: str               # "extreme" or "cluster"
    state: PsychrometricState     # full psychrometric properties
    cluster_id: int | None        # None for extremes
    hours_in_cluster: int | None  # None for extremes

@dataclass
class DesignConditionResult:
    location: EPWLocation
    design_points: list[DesignPoint]
    cluster_infos: list[ClusterInfo]
    all_hourly_states: list[PsychrometricState]  # for chart plotting
    labels: list[int]                             # cluster assignment per hour
```

---

## 4. Backend API

### 4.1 Endpoints

#### POST `/api/weather/upload`

Accepts an EPW file upload, processes it through the full pipeline, and returns results.

**Request**: `multipart/form-data` with a single file field named `file`.

**Query parameters**:
- `n_clusters` (optional, default 5): Number of clusters for k-means
- `unit_system` (optional, default "IP"): "IP" for imperial, "SI" for metric

**Response** (JSON):

```json
{
    "location": {
        "city": "Los Angeles",
        "state": "CA",
        "country": "USA",
        "latitude": 33.94,
        "longitude": -118.4,
        "elevation_m": 30.0
    },
    "design_points": [
        {
            "label": "Peak Cooling",
            "point_type": "extreme",
            "dry_bulb": 104.2,
            "wet_bulb": 71.1,
            "dewpoint": 58.3,
            "humidity_ratio": 73.2,
            "enthalpy": 37.8,
            "relative_humidity": 0.18,
            "specific_volume": 14.72,
            "month": 8,
            "day": 15,
            "hour": 15,
            "cluster_id": null,
            "hours_in_cluster": null
        },
        {
            "label": "Peak Heating",
            "point_type": "extreme",
            "...": "..."
        },
        {
            "label": "Peak Dehumidification",
            "point_type": "extreme",
            "...": "..."
        },
        {
            "label": "Cluster 1 — Warm Dry",
            "point_type": "cluster_worst_case",
            "...": "...",
            "cluster_id": 0,
            "hours_in_cluster": 1740
        }
    ],
    "chart_data": {
        "hourly_points": [
            {
                "dry_bulb": 58.3,
                "humidity_ratio": 42.1,
                "cluster_id": 2
            }
        ]
    },
    "cluster_summary": [
        {
            "cluster_id": 0,
            "label": "Warm Dry",
            "hour_count": 1740,
            "fraction_of_year": 0.199,
            "centroid_dry_bulb": 88.3,
            "centroid_humidity_ratio": 54.1
        }
    ]
}
```

**Notes on the `chart_data.hourly_points` array**:
- This array will have 8,760 entries. To keep response size manageable, include only `dry_bulb`, `humidity_ratio`, and `cluster_id` per point (these are what the frontend needs to plot and color-code).
- The full psychrometric state is only included for the design points, not all 8,760 hours.

#### GET `/api/weather/status`

Health check / feature availability endpoint. Returns whether the required dependencies (scikit-learn, numpy) are available.

### 4.2 Error Handling

Return clear HTTP error responses:
- `400` if the file is not a valid EPW file (with descriptive message)
- `400` if n_clusters is out of valid range (suggest 3–10)
- `422` if the file has corrupt or missing data that prevents analysis
- `500` for unexpected server errors

---

## 5. Frontend Integration

### 5.1 File Upload UI

Add a section (could be a sidebar panel, modal, or dedicated tab) with:

1. A file upload input accepting `.epw` files
2. An optional slider or dropdown for number of clusters (default 5, range 3–10)
3. A "Process" button
4. A loading indicator (processing 8,760 points takes a moment)

### 5.2 Chart Overlay

After processing, add the following traces to the existing Plotly.js psychrometric chart:

**Weather data scatter trace**:
- Plot all 8,760 points as small, semi-transparent markers
- X-axis: dry-bulb temperature
- Y-axis: humidity ratio
- Color-code by cluster assignment (use a qualitative color palette — e.g., Plotly's built-in qualitative scales, or manually assign 5–8 distinct colors)
- Marker size: small (3–4px) to avoid visual clutter
- Opacity: 0.3–0.5 so overlapping points create a density effect

**Design point markers**:
- Plot the extracted design points as larger, prominent markers (size 12–15px)
- Use distinct marker shapes: circle for cluster worst-case, star or diamond for extremes
- Add hover text showing the full psychrometric state and the point label
- These should be visually dominant over the weather data scatter

**Cluster centroids** (optional but helpful):
- Plot as medium-sized markers (8–10px) with an "X" or "+" shape
- Label with "Centroid" in hover text

### 5.3 Summary Table

Display a table (below the chart or in a sidebar) showing each design point with all properties. This table should be:

- Sortable by any column
- Show units in the column headers appropriate to the user's selected unit system
- Highlight extreme points differently from cluster points (e.g., bold the extreme rows)
- Include the hour count and fraction-of-year for cluster points

### 5.4 Interaction Between Weather Data and Existing Chart Features

The weather data overlay should be toggleable — the user should be able to show/hide it without losing the data. If the user has existing state points plotted on the chart (from PsychroApp's existing state point management feature), both should coexist on the same chart.

---

## 6. Cluster Labeling Strategy

### 6.1 Automatic Labeling

Rather than showing "Cluster 0", "Cluster 1", etc., assign descriptive labels based on the centroid's position on the psychrometric chart. A simple heuristic:

```python
def label_cluster(centroid_db_f: float, centroid_rh: float) -> str:
    """
    Assign a descriptive label based on centroid conditions.
    centroid_db_f: dry-bulb in °F
    centroid_rh: relative humidity as fraction (0-1)
    """
    if centroid_db_f >= 90:
        temp_label = "Hot"
    elif centroid_db_f >= 75:
        temp_label = "Warm"
    elif centroid_db_f >= 60:
        temp_label = "Mild"
    elif centroid_db_f >= 45:
        temp_label = "Cool"
    else:
        temp_label = "Cold"

    if centroid_rh >= 0.65:
        moisture_label = "Humid"
    elif centroid_rh >= 0.35:
        moisture_label = "Moderate"
    else:
        moisture_label = "Dry"

    return f"{temp_label} {moisture_label}"
```

This produces labels like "Warm Humid", "Cool Dry", "Hot Moderate", etc., which immediately tell the designer what kind of operating condition the cluster represents.

---

## 7. Testing Strategy

### 7.1 EPW Parser Tests

- Test with a known EPW file (download one from energyplus.net/weather for a well-known location like Los Angeles or Chicago)
- Verify location metadata extraction matches expected values
- Verify hourly record count is 8,760
- Verify a spot-checked hour (e.g., the first hour of the file) matches the expected values
- Test error handling: truncated file, wrong format, missing data markers

### 7.2 Psychrometric Calculation Tests

- Compute states for a set of known input conditions and verify against published psychrometric tables or an online calculator
- Example: At standard pressure (101325 Pa), 35°C DB, 20°C DP → verify the computed WB, ω, h, RH, v match expected values within acceptable tolerance (0.1% for most properties)
- Test edge cases: 0°C DB, very high humidity, very low humidity

### 7.3 Clustering Tests

- With synthetic data (e.g., two well-separated Gaussian blobs), verify k=2 correctly separates them
- Verify centroid inverse transformation returns values in the expected range
- Verify hour counts sum to 8,760
- Verify worst-case extraction returns the actual highest-enthalpy point per cluster

### 7.4 Integration Tests

- Run the full pipeline on a real EPW file
- Verify the number of design points equals 3 (extremes) + n_clusters
- Verify peak cooling enthalpy ≥ all other points' enthalpy
- Verify peak heating DB ≤ all other points' DB
- Verify cluster hour counts sum to 8,760

### 7.5 API Tests

- Test file upload with a valid EPW file, verify 200 response with expected structure
- Test with an invalid file, verify 400 response
- Test with different n_clusters values

---

## 8. Dependencies

Add to `requirements.txt`:

```
scikit-learn>=1.3.0
numpy>=1.24.0
psychrolib>=2.5.0
```

These are in addition to existing PsychroApp dependencies (FastAPI, uvicorn, etc.).

---

## 9. Implementation Sequence

Implement in this order, testing each module before moving to the next:

1. **`epw_parser.py`** + tests — Get a clean data pipeline from file to structured records
2. **`psychrometric_calc.py`** + tests — Compute full states from parsed records
3. **`clustering.py`** + tests — Cluster the states and extract per-cluster info
4. **`design_extractor.py`** + tests — Orchestrate the pipeline and extract design points
5. **Backend API endpoint** + tests — Wire up the file upload and response
6. **Frontend: file upload + chart overlay** — Display the 8,760 points and design points
7. **Frontend: summary table** — Show the design points in tabular form
8. **Polish: cluster labeling, toggle visibility, unit conversions** — Refine the user experience

---

## 10. File Size and Performance Considerations

- An EPW file is ~1.5–2.5 MB of text. Parsing is fast (< 1 second).
- Computing 8,760 psychrometric states with psychrolib takes < 1 second on modern hardware.
- K-means on 8,760 × 2 features with k=5 converges in milliseconds.
- The response JSON with 8,760 chart points is roughly 300–500 KB. This is acceptable for a single upload workflow.
- If response size becomes a concern, the chart data points could be downsampled (e.g., every 3rd hour = 2,920 points) with minimal visual impact, but this should not be necessary for the initial implementation.

---

## 11. Future Enhancements (Out of Scope for Initial Implementation)

These are noted for context but should **not** be implemented now:

- **Automatic k selection** using silhouette scores or elbow method
- **Monthly or seasonal filtering** — analyze only summer months, or only occupied hours
- **System performance overlay** — plot the HVAC system's capacity envelope on the same chart to visually identify where the system can't meet conditions
- **Load calculation integration** — compute building loads at each design point, not just outdoor conditions
- **Multiple weather file comparison** — overlay two climate locations on the same chart
- **ASHRAE design condition comparison** — plot the ASHRAE published design conditions alongside the extracted points to show how they compare