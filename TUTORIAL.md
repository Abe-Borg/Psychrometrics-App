# Psychrometrics App -- Tutorial & User's Manual

## Table of Contents

1. [Overview](#1-overview)
2. [Getting Started](#2-getting-started)
3. [Application Layout](#3-application-layout)
4. [Toolbar Reference](#4-toolbar-reference)
5. [State Points](#5-state-points)
6. [Psychrometric Processes](#6-psychrometric-processes)
7. [Coil Analysis](#7-coil-analysis)
8. [SHR Tools](#8-shr-tools)
9. [Airflow Calculator](#9-airflow-calculator)
10. [AHU Wizard](#10-ahu-wizard)
11. [ASHRAE Design Days](#11-ashrae-design-days)
12. [TMY Weather Data](#12-tmy-weather-data)
13. [Chart Interactions](#13-chart-interactions)
14. [Project Management](#14-project-management)
15. [Keyboard Shortcuts](#15-keyboard-shortcuts)
16. [Unit Systems & Pressure](#16-unit-systems--pressure)
17. [Glossary of Terms](#17-glossary-of-terms)

---

## 1. Overview

The Psychrometrics App is a web-based tool for HVAC engineers, students, and
anyone who works with moist-air thermodynamics. It provides an interactive
psychrometric chart with a full suite of calculation tools:

- **State point resolution** -- enter any two known air properties and compute
  all remaining psychrometric properties.
- **Process simulation** -- model 12 different air-handling processes (heating,
  cooling, dehumidification, mixing, evaporative cooling, and more) and
  visualize them on the chart.
- **Coil analysis** -- forward (ADP + bypass factor) and reverse (leaving
  conditions) cooling coil analysis with sensible/latent load breakdown.
- **SHR line plotting** -- draw Room SHR lines and compute GSHR / ESHR for
  full system analysis.
- **Airflow & load calculator** -- solve for Q, airflow, or delta using the
  standard HVAC load equations.
- **Condensation checker** -- determine whether a given surface will condense
  moisture from the surrounding air.
- **AHU Wizard** -- step-by-step air handling unit sizing that computes mixed
  air, coil leaving, reheat, and supply conditions automatically.
- **ASHRAE Design Day data** -- search for any city and overlay its design
  cooling/heating conditions on the chart.
- **TMY weather data** -- upload an EPW or CSV weather file and visualize
  8,760 hours as a scatter plot or frequency heatmap on the chart.
- **Project save/load** -- save your work as a JSON file, reload it later, and
  export as PNG, SVG, CSV, or a full PDF report.

The application supports both **IP (Imperial)** and **SI (Metric)** unit
systems and adjustable barometric pressure / altitude.

---

## 2. Getting Started

### Running the Application

1. **Start the backend** (Python / FastAPI):
   ```bash
   pip install -r requirements.txt
   python run_backend.py
   ```
2. **Start the frontend** (React / Vite):
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open your browser and navigate to the URL shown in the terminal (typically
   `http://localhost:5173`).

When the page loads, the psychrometric chart is drawn at standard sea-level
pressure (14.696 psia for IP, 101325 Pa for SI). The right-hand sidebar
contains all the calculation panels.

---

## 3. Application Layout

The interface has three main regions:

```
+------------------------------------------------------+
|  TOOLBAR (project title, save/load, export, units)   |
+------------------------------------+-----------------+
|                                    |                 |
|                                    |   SIDEBAR       |
|     PSYCHROMETRIC CHART            |   (scrollable)  |
|     (interactive Plotly chart)     |                 |
|                                    |  - State Points |
|                                    |  - Processes    |
|                                    |  - Coil         |
|                                    |  - SHR          |
|                                    |  - Airflow      |
|                                    |  - AHU Wizard   |
|                                    |  - Design Days  |
|                                    |  - TMY Data     |
+------------------------------------+-----------------+
```

- **Toolbar** -- spans the top of the window. Contains project management
  controls, unit system toggle, altitude/pressure inputs, undo/redo, export
  menu, and dark/light theme toggle.
- **Chart** -- occupies the left portion. Fully interactive: hover for
  property readouts, click to add points, scroll to zoom, drag to pan.
- **Sidebar** -- occupies the right portion. Contains all calculation panels,
  organized into collapsible sections. You can resize it by dragging the
  divider handle, or collapse it entirely by clicking the arrow button on
  the divider.

### Layers Panel

In the top-left corner of the chart, a **"Layers"** button opens a checkbox
panel that controls which overlays are visible:

| Layer           | Controls                                       |
| --------------- | ---------------------------------------------- |
| RH Lines        | Constant relative humidity curves              |
| Wet-Bulb Lines  | Constant wet-bulb temperature lines            |
| Enthalpy Lines  | Constant enthalpy lines                        |
| Volume Lines    | Constant specific volume lines                 |
| State Points    | All plotted state points                       |
| Processes       | All process paths and arrows                   |
| Coil Path       | Coil analysis entering-to-leaving path         |
| SHR Lines       | Room SHR, GSHR, and ESHR lines                 |
| Design Days     | ASHRAE design day condition markers             |
| TMY Data        | TMY scatter or heatmap overlay                 |

---

## 4. Toolbar Reference

From left to right, the toolbar contains:

### Project Title
Click the title text to rename your project. Press Enter or click away to
confirm. This name is used in exported filenames.

### Save / Load
- **Save** -- downloads the current project as a `.json` file. Keyboard
  shortcut: `Ctrl+S` (or `Cmd+S` on macOS).
- **Load** -- opens a file picker to import a previously saved `.json`
  project file. All state points, processes, coil results, and SHR data are
  restored.

### Export Menu
Click **Export** to reveal a dropdown with four options:

| Option         | Description                                      |
| -------------- | ------------------------------------------------ |
| Chart as PNG   | Raster image of the current chart view           |
| Chart as SVG   | Vector image of the current chart view           |
| Data as CSV    | Spreadsheet of all state points and processes    |
| PDF Report     | Full report with chart image, tables, and data   |

### Undo / Redo
- **Undo** (&#8630;) -- reverts the last change to state points, processes,
  coil, or SHR data. Keyboard shortcut: `Ctrl+Z`.
- **Redo** (&#8631;) -- restores the last undone change. Keyboard shortcut:
  `Ctrl+Shift+Z` or `Ctrl+Y`.

Up to 50 undo steps are retained.

### Unit System Toggle
Click the button showing either **IP (°F)** or **SI (°C)** to switch
between Imperial and Metric units. Switching resets the chart to standard
pressure and clears processes (since they are unit-dependent).

### Altitude & Pressure
- **Alt** -- enter an altitude value. When you press Enter or click away, the
  app calculates the corresponding barometric pressure using the standard
  atmosphere model.
- **P** -- directly enter a barometric pressure. Changing pressure regenerates
  the chart curves and clears existing processes.

### Theme Toggle
The sun/moon icon in the far right toggles between **dark mode** and **light
mode**.

---

## 5. State Points

A state point represents a specific condition of moist air. It is the
fundamental building block of all psychrometric analysis.

### Adding a State Point

In the **Add State Point** section of the sidebar:

1. **Select an input pair** from the dropdown. Available pairs:
   - Tdb + RH (dry-bulb temperature + relative humidity)
   - Tdb + Twb (dry-bulb + wet-bulb)
   - Tdb + Tdp (dry-bulb + dew point)
   - Tdb + W (dry-bulb + humidity ratio in lb/lb or kg/kg)
   - Tdb + h (dry-bulb + enthalpy)
   - Twb + RH
   - Tdp + RH

2. **Enter the two values** in the input fields.

3. **(Optional)** Enter a **label** (e.g., "Room", "OA", "Supply").

4. Click **Add Point**.

The backend resolves all remaining psychrometric properties and the point
appears on the chart and in the **State Points** list.

### Click-to-Add from the Chart

Click anywhere on the chart area (not on an existing point) and the
**Tdb + W** fields in the State Point form will auto-fill with the clicked
coordinates. You can adjust the values or just click **Add Point**.

### State Point Properties

Expand any state point card in the list to see all computed properties:

| Property         | Symbol | IP Units   | SI Units   |
| ---------------- | ------ | ---------- | ---------- |
| Dry-Bulb Temp    | Tdb    | °F         | °C         |
| Wet-Bulb Temp    | Twb    | °F         | °C         |
| Dew Point        | Tdp    | °F         | °C         |
| Relative Humidity| RH     | %          | %          |
| Humidity Ratio   | W      | lb/lb      | kg/kg      |
| Humidity Ratio   | W_disp | gr/lb      | g/kg       |
| Enthalpy         | h      | BTU/lb     | kJ/kg      |
| Specific Volume  | v      | ft³/lb     | m³/kg      |
| Vapor Pressure   | Pv     | psi        | Pa         |
| Saturation Press | Ps     | psi        | Pa         |
| Degree of Sat.   | mu     | (ratio)    | (ratio)    |

### Managing State Points

- **Select** a point by clicking its card (or clicking its marker on the
  chart). Selected points are highlighted with a ring.
- **Delete** a selected point by pressing the `Delete` or `Backspace` key, or
  click the **X** button on the card.
- **Clear all** -- appears when two or more points exist.
- **Deselect** by pressing `Escape` or clicking the same card again.

---

## 6. Psychrometric Processes

A process transforms air from one state to another. The app supports 12
process types.

### Adding a Process

In the **Add Process** section of the sidebar:

1. **Select Process Type** from the dropdown.
2. **Enter Start Point** using any input pair (same options as state points).
3. Fill in the **process-specific parameters** (vary by type -- see below).
4. Click **Add Process**.

### Process Chaining

If you have already added one or more processes, a **"Chain from Process N
end point"** checkbox appears. When checked, the previous process's end
point is automatically used as the start point of the new process. This is
useful for modeling sequential AHU operations (e.g., mixing -> cooling ->
reheat).

### Right-Click to Start a Process

Right-click on any state point's marker on the chart. The Process Builder
will auto-fill its start point fields with that point's Tdb and RH values.

### Process Types and Parameters

#### Sensible Heating / Sensible Cooling / Sensible Reheat

Changes dry-bulb temperature while keeping humidity ratio constant.

| Mode              | Required Fields                                   |
| ----------------- | ------------------------------------------------- |
| Target Tdb        | Target dry-bulb temperature                       |
| Delta T           | Temperature difference (positive = direction)     |
| Q + Airflow       | Sensible heat load (BTU/hr or W) + airflow (CFM or m³/s) |

#### Cooling & Dehumidification

Cools air past the dew point, removing both sensible and latent heat.

| Mode              | Required Fields                                   |
| ----------------- | ------------------------------------------------- |
| Forward (ADP + BF)| Apparatus dew point temperature + bypass factor (0-1) |
| Reverse           | Leaving dry-bulb temperature + leaving RH         |

#### Adiabatic Mixing

Mixes two airstreams at different conditions.

| Required Fields                                              |
| ------------------------------------------------------------ |
| Stream 2 input pair and values (same options as state points)|
| Stream 1 mass fraction (0-1): proportion of stream 1         |

The mixed condition lies on the straight line between the two stream
states, positioned according to the mass fraction.

#### Steam Humidification

Adds moisture at approximately constant dry-bulb temperature (pure steam
injection follows a nearly vertical path on the chart).

| Mode       | Required Fields                                 |
| ---------- | ----------------------------------------------- |
| Target RH  | Desired final relative humidity (%)             |
| Target W   | Desired final humidity ratio (lb/lb or kg/kg)   |

#### Adiabatic Humidification

Evaporates water into the air along a constant wet-bulb line. Dry-bulb
temperature drops while humidity rises.

| Mode          | Required Fields                                |
| ------------- | ---------------------------------------------- |
| Effectiveness | Wet-bulb effectiveness (0-1)                   |
| Target RH     | Desired final relative humidity (%)            |

#### Heated Water Spray

Humidification using heated water. The process path direction depends on
the water temperature relative to the air wet-bulb.

| Required Fields                                 |
| ----------------------------------------------- |
| Water temperature (°F or °C)                    |
| Effectiveness (0-1)                             |

#### Direct Evaporative Cooling

Adiabatic cooling along the wet-bulb line (same physics as adiabatic
humidification, but oriented as a cooling operation).

| Required Fields       |
| --------------------- |
| Effectiveness (0-1)   |

#### Indirect Evaporative Cooling

Sensible cooling only -- the primary airstream is cooled without adding
moisture, using a secondary wet airstream in a heat exchanger.

| Required Fields       |
| --------------------- |
| Effectiveness (0-1)   |

#### Indirect-Direct Evaporative (Two-Stage)

Combines indirect and direct evaporative cooling in series. The first
stage reduces dry-bulb sensibly; the second stage adds moisture along the
wet-bulb line.

| Required Fields               |
| ----------------------------- |
| IEC effectiveness (0-1)       |
| DEC effectiveness (0-1)       |

#### Chemical Dehumidification

Uses a desiccant to remove moisture. The process follows a constant-
enthalpy path (dry-bulb rises as humidity ratio drops).

| Mode       | Required Fields                                |
| ---------- | ---------------------------------------------- |
| Target W   | Desired final humidity ratio (lb/lb or kg/kg)  |
| Target RH  | Desired final relative humidity (%)            |

### Process List

Each computed process appears as a card in the **Processes** section, showing:
- Process number and type
- Start and end temperatures
- Expandable detail panel with all metadata (delta T, loads, SHR, etc.)
- Chain indicator (vertical connector line) when chained to the previous
  process

Processes are drawn on the chart as colored directional paths with arrows
and numbered labels.

---

## 7. Coil Analysis

The **Coil Analysis** panel performs a detailed analysis of a cooling coil,
computing the entering and leaving air states, the apparatus dew point (ADP),
bypass factor (BF), contact factor (CF), and the sensible/latent/total load
breakdown.

### Forward Mode (ADP + BF)

Given the entering air conditions and the coil's ADP and bypass factor, the
tool computes the leaving air conditions and loads.

| Required Fields                                                |
| -------------------------------------------------------------- |
| Entering air input pair + values                               |
| ADP dry-bulb temperature                                       |
| Bypass factor (0 < BF < 1)                                    |

### Reverse Mode (Leaving Conditions)

Given the entering and leaving air conditions, the tool back-calculates the
ADP, bypass factor, and loads.

| Required Fields                                                |
| -------------------------------------------------------------- |
| Entering air input pair + values                               |
| Leaving air input pair + values                                |

### Optional Fields

- **Airflow** (CFM or m³/s) -- when provided, loads are reported in BTU/hr
  (or Watts) rather than per-unit-mass.
- **Water entering / leaving temperatures** -- when both are provided, the
  tool computes the chilled water flow rate (GPM or L/s).

### Coil Results

The results panel shows:
- ADP temperature
- Bypass factor and contact factor
- Sensible load (Qs), latent load (Ql), total load (Qt)
- Sensible Heat Ratio (SHR)
- Water flow rate (if water temps provided)

The coil path is drawn on the chart as a cyan line from entering to leaving,
with the ADP marked as a star on the saturation curve.

---

## 8. SHR Tools

The SHR (Sensible Heat Ratio) tools section has two sub-panels:

### Room SHR Line

Draws a line on the chart from a room design condition along the slope
defined by the SHR. The line extends to the saturation curve, and its
intersection is the required ADP (apparatus dew point) for a coil serving
that room.

| Required Fields                              |
| -------------------------------------------- |
| Room state input pair + values               |
| SHR value (0-1)                              |

You can add multiple SHR lines. Each appears as a dashed red line on the
chart with a star marker at its ADP.

### GSHR / ESHR Calculator

Performs a full Grand Sensible Heat Ratio (GSHR) and Effective Sensible
Heat Ratio (ESHR) analysis. This is the core method used when designing
a central air system with outdoor air.

| Required Fields                                      |
| ---------------------------------------------------- |
| Room state input pair + values                       |
| Outdoor air (OA) state input pair + values           |
| Room sensible load Qs (BTU/hr or W)                 |
| Room total load Qt (BTU/hr or W)                    |
| OA fraction (0-1)                                    |
| Total airflow (CFM or m³/s)                          |
| Bypass factor for ESHR (optional, 0-1)               |

The results include:
- Room SHR, GSHR, and (if BF provided) ESHR values
- ADP for each SHR line
- Mixed air point (plotted as a triangle on the chart)
- All three SHR lines plotted on the chart in different dash styles

---

## 9. Airflow Calculator

The **Airflow Calculator** solves the fundamental HVAC load equation:

```
Q = C * airflow * delta
```

where C is the constant factor (includes air density and specific heat or
latent heat constant, depending on the load type).

### Load Types

| Load Type  | Delta Meaning                          | C Factor Basis            |
| ---------- | -------------------------------------- | ------------------------- |
| Sensible   | Temperature difference (delta T)       | density * Cp * 60         |
| Latent     | Humidity ratio difference (delta W)    | density * hfg * 60        |
| Total      | Enthalpy difference (delta h)          | density * 60              |

### Solve Modes

| Mode            | Known Inputs    | Computed Output |
| --------------- | --------------- | --------------- |
| Solve for Q     | Airflow + Delta | Q (load)        |
| Solve for Airflow | Q + Delta     | Airflow         |
| Solve for Delta | Q + Airflow     | Delta           |

### Optional Reference Conditions

You can provide reference dry-bulb temperature and humidity ratio to fine-tune
the air density used in the C factor calculation.

### Auto-Fill from Process

If you have computed processes, the auto-fill dropdown lets you select any
process and automatically populate the delta value (temperature difference,
humidity ratio difference, or enthalpy difference) and reference conditions
from that process's start point.

### Condensation Checker

Expand the **Condensation Checker** sub-panel to determine whether moisture
will condense on a surface.

| Required Fields                                        |
| ------------------------------------------------------ |
| Surface temperature (°F or °C)                         |
| Air state input pair + values                          |

The tool compares the surface temperature to the air's dew point and reports:
- Whether condensation will occur
- The dew point of the air
- The margin (surface temp minus dew point)

You can auto-fill the air state from any existing state point.

---

## 10. AHU Wizard

The **AHU Wizard** guides you through a step-by-step Air Handling Unit
design. It supports three AHU configurations:

| AHU Type       | Description                                    |
| -------------- | ---------------------------------------------- |
| Mixed Air      | Standard OA + RA mixing box                   |
| 100% Outside Air | DOAS / no return air                        |
| Economizer     | Variable OA fraction                           |

### Wizard Steps

1. **AHU Type** -- select the system configuration.
2. **Outside Air** -- enter outdoor dry-bulb and coincident wet-bulb (or RH).
   If you have loaded ASHRAE design day data, click "Pre-fill from design day
   data" to auto-populate.
3. **Return Air** -- (mixed air and economizer only) enter return air Tdb and
   RH. Typical values: 75°F / 50% RH.
4. **Mixing** -- (mixed air and economizer only) enter the outside air mass
   fraction (0-1).
5. **Supply Target** -- enter the desired supply air dry-bulb temperature.
   Optionally enter supply RH and room sensible load for airflow sizing.
6. **Calculate** -- review inputs and click Calculate.

### Results

The wizard computes:
- All intermediate state points (OA, RA, Mixed, Coil Leaving, Supply)
- Cooling loads (Qs, Ql, Qt) per unit mass of air
- SHR of the cooling process
- Reheat load (if the coil leaving temperature is below the supply target)
- Supply airflow (if room sensible load was provided)

Click **"Apply to Chart"** to add all computed state points and process paths
to the main chart.

---

## 11. ASHRAE Design Days

The **ASHRAE Design Days** panel lets you look up published design conditions
for thousands of locations worldwide.

### Usage

1. Start typing a city name in the search box.
2. A dropdown of matching locations appears, showing city, state/country, and
   ASHRAE climate zone.
3. Click a location to select it.
4. Click **Load Conditions** to fetch all design conditions.

### What Gets Loaded

The app loads multiple design conditions for the selected location:
- **Cooling** design day conditions (shown as orange upward triangles)
- **Heating** design day conditions (shown as blue downward triangles)

Each point includes dry-bulb, wet-bulb, dew point, RH, humidity ratio, and
enthalpy.

The points are overlaid on the chart and listed in a scrollable summary panel.
Click **Clear** to remove them.

---

## 12. TMY Weather Data

The **TMY Weather Data** panel lets you upload a Typical Meteorological Year
file and visualize all 8,760 hourly data points on the psychrometric chart.

### Supported File Formats

- **EPW** -- EnergyPlus Weather file (standard format from the DOE weather
  database)
- **CSV** -- comma-separated values with temperature and humidity columns

### Display Modes

After uploading, toggle between:
- **Scatter** -- each hour is a dot, color-coded by month (January = cool
  colors, July = warm colors). Opacity is low so density patterns emerge.
- **Heatmap** -- hours are binned into a temperature/humidity grid. Cell
  color intensity represents the number of hours in each bin.

Click **Clear TMY Data** to remove the overlay.

---

## 13. Chart Interactions

The Plotly-based chart supports several interactive features:

### Hover Tooltip

Move your cursor over the chart area. A floating tooltip appears showing
the psychrometric properties at the cursor position:
Tdb, W, RH, Twb, Tdp, h, v.

### Click-to-Add

Click on an empty area of the chart. The state point form auto-fills with
the Tdb and W at the clicked location. Adjust if needed, then click
**Add Point**.

### Click on State Point

Click on a plotted state point marker to select it. The corresponding card
in the sidebar is highlighted. Press `Delete` to remove it.

### Zoom

Scroll the mouse wheel to zoom in/out. Drag to pan the chart.

### Mode Bar

The Plotly mode bar (top-right of chart area) provides:
- Zoom tool
- Pan tool
- Zoom-to-fit (reset axes)
- Download plot as PNG

### Process Arrows

Processes are drawn with directional arrows showing the air path direction.
Numbered labels appear at the midpoint of each process line.

---

## 14. Project Management

### Saving a Project

Click **Save** in the toolbar (or press `Ctrl+S`). A JSON file is
downloaded containing:
- Project title
- Unit system and pressure settings
- All state points with full properties
- All processes with metadata
- Coil analysis results
- SHR lines and GSHR results

### Loading a Project

Click **Load** and select a previously saved `.json` file. The entire
application state is restored including all points, processes, and overlays.

### Exporting

Use the **Export** dropdown for:
- **Chart as PNG** -- high-resolution raster screenshot of the chart
- **Chart as SVG** -- scalable vector format (ideal for publications)
- **Data as CSV** -- a spreadsheet listing all state point properties and
  process start/end conditions
- **PDF Report** -- a complete report containing the chart image, state
  point tables, process details, coil analysis, and SHR data

---

## 15. Keyboard Shortcuts

| Shortcut             | Action                                    |
| -------------------- | ----------------------------------------- |
| `Ctrl+Z`             | Undo                                      |
| `Ctrl+Shift+Z`       | Redo                                      |
| `Ctrl+Y`             | Redo (alternative)                        |
| `Ctrl+S`             | Save project                              |
| `Delete` / `Backspace` | Remove selected state point             |
| `Escape`             | Deselect state point                      |

Note: Keyboard shortcuts are disabled when a text input field is focused.

---

## 16. Unit Systems & Pressure

### IP (Imperial) Units

| Property         | Unit        |
| ---------------- | ----------- |
| Temperature      | °F          |
| Humidity Ratio   | gr/lb (display), lb/lb (calculation) |
| Enthalpy         | BTU/lb      |
| Specific Volume  | ft³/lb      |
| Pressure         | psia        |
| Airflow          | CFM         |
| Heat Load        | BTU/hr      |
| Altitude         | ft          |

### SI (Metric) Units

| Property         | Unit        |
| ---------------- | ----------- |
| Temperature      | °C          |
| Humidity Ratio   | g/kg (display), kg/kg (calculation) |
| Enthalpy         | kJ/kg       |
| Specific Volume  | m³/kg       |
| Pressure         | Pa          |
| Airflow          | m³/s        |
| Heat Load        | W           |
| Altitude         | m           |

### Adjusting Pressure

Barometric pressure affects all psychrometric calculations. The default is
standard sea-level pressure. To analyze conditions at elevation:

1. Enter the altitude in the **Alt** field and press Enter. The app
   calculates the corresponding pressure automatically.
2. Or enter the pressure directly in the **P** field.

Changing the pressure regenerates the chart and clears existing processes
(since they were computed at the old pressure).

---

## 17. Glossary of Terms

| Term    | Definition                                                                 |
| ------- | -------------------------------------------------------------------------- |
| **Tdb** | Dry-bulb temperature -- the "ordinary" air temperature measured by a standard thermometer. |
| **Twb** | Wet-bulb temperature -- the temperature measured by a thermometer with a wet wick, reflecting evaporative cooling potential. |
| **Tdp** | Dew point temperature -- the temperature at which moisture begins to condense from the air. |
| **RH**  | Relative humidity -- the ratio of actual water vapor pressure to the saturation pressure at the same temperature, expressed as a percentage. |
| **W**   | Humidity ratio -- the mass of water vapor per unit mass of dry air. |
| **h**   | Enthalpy -- the total heat content of the moist air per unit mass of dry air. |
| **v**   | Specific volume -- the volume of moist air per unit mass of dry air. |
| **Pv**  | Water vapor partial pressure. |
| **Ps**  | Saturation pressure at the given dry-bulb temperature. |
| **mu**  | Degree of saturation -- the ratio of actual humidity ratio to the saturation humidity ratio at the same temperature. |
| **ADP** | Apparatus Dew Point -- the surface temperature of a cooling coil. Air leaving the coil lies on the line connecting the entering condition to the ADP on the saturation curve. |
| **BF**  | Bypass Factor -- the fraction of air that passes through a coil without contacting the coil surface. BF = 0 means perfect contact; BF = 1 means no contact. |
| **CF**  | Contact Factor -- equals 1 - BF. The fraction of air that fully contacts the coil. |
| **SHR** | Sensible Heat Ratio -- the ratio of sensible heat to total heat (sensible + latent). |
| **GSHR**| Grand Sensible Heat Ratio -- accounts for the total system including outdoor air and room loads. |
| **ESHR**| Effective Sensible Heat Ratio -- accounts for coil bypass factor in the SHR calculation. |
| **TMY** | Typical Meteorological Year -- a dataset of hourly weather data representing typical conditions for a location. |
| **EPW** | EnergyPlus Weather file format. |
| **CFM** | Cubic Feet per Minute -- volumetric airflow rate in IP units. |
| **GPM** | Gallons Per Minute -- water flow rate. |
| **DOAS**| Dedicated Outdoor Air System -- an AHU that handles 100% outside air. |
