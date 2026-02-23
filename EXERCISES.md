# Psychrometrics App -- Exercises

These exercises are designed to teach you the complete functionality of the
Psychrometrics App. Work through them sequentially -- each section builds on
skills from previous sections. Answers and expected results are provided at
the end.

---

## Table of Contents

- [Exercise Set 1: Getting Oriented](#exercise-set-1-getting-oriented)
- [Exercise Set 2: State Points](#exercise-set-2-state-points)
- [Exercise Set 3: Psychrometric Processes](#exercise-set-3-psychrometric-processes)
- [Exercise Set 4: Process Chaining](#exercise-set-4-process-chaining)
- [Exercise Set 5: Coil Analysis](#exercise-set-5-coil-analysis)
- [Exercise Set 6: SHR Tools](#exercise-set-6-shr-tools)
- [Exercise Set 7: Airflow Calculator](#exercise-set-7-airflow-calculator)
- [Exercise Set 8: AHU Wizard](#exercise-set-8-ahu-wizard)
- [Exercise Set 9: ASHRAE Design Days](#exercise-set-9-ashrae-design-days)
- [Exercise Set 10: TMY Weather Data](#exercise-set-10-tmy-weather-data)
- [Exercise Set 11: Chart Interactions & Layers](#exercise-set-11-chart-interactions--layers)
- [Exercise Set 12: Project Management & Export](#exercise-set-12-project-management--export)
- [Exercise Set 13: Unit System & Pressure](#exercise-set-13-unit-system--pressure)
- [Exercise Set 14: Integrated Design Problem](#exercise-set-14-integrated-design-problem)
- [Answers & Expected Results](#answers--expected-results)

---

## Exercise Set 1: Getting Oriented

**Objective:** Familiarize yourself with the application layout, toolbar, and
basic navigation.

### Exercise 1.1 -- Explore the Interface
1. Open the application. Identify the three main regions: toolbar, chart, and
   sidebar.
2. Locate the **Layers** button in the top-left corner of the chart. Click it
   and note the 10 layer toggles available.
3. Scroll through the sidebar and list all the section headings you see.

### Exercise 1.2 -- Toolbar Basics
1. Click on the project title in the toolbar. Rename it to "My First Project".
   Press Enter to confirm.
2. Find the unit system toggle button. What unit system is shown by default?
3. What are the default values for altitude and pressure?
4. Find the theme toggle (sun/moon icon). Click it to switch to light mode,
   then switch back to dark mode.

### Exercise 1.3 -- Chart Navigation
1. Hover your mouse over the chart. Observe the floating tooltip that appears.
   What properties does it display?
2. Use the scroll wheel to zoom in on the region around 75°F and 50% RH.
3. Drag the chart to pan around.
4. Use the Plotly mode bar's "Reset axes" button (house icon) to return to the
   default view.

---

## Exercise Set 2: State Points

**Objective:** Learn to create, inspect, select, and delete state points
using all available input pairs.

### Exercise 2.1 -- Add a Point Using Tdb + RH
1. In the **Add State Point** section, select the input pair **Tdb + RH**.
2. Enter Tdb = **75** and RH = **50**.
3. Enter the label **"Room"**.
4. Click **Add Point**.
5. Verify the point appears on the chart and in the State Points list.

### Exercise 2.2 -- Add a Point Using Tdb + Twb
1. Change the input pair to **Tdb + Twb**.
2. Enter Tdb = **95** and Twb = **78**.
3. Label it **"Outdoor"**.
4. Click **Add Point**.
5. Expand the "Outdoor" card in the State Points list. Record the following
   computed properties: RH, W (gr/lb), h, Tdp.

### Exercise 2.3 -- Add a Point Using Tdb + Tdp
1. Select **Tdb + Tdp**.
2. Enter Tdb = **55** and Tdp = **53**.
3. Label it **"Supply"**.
4. Click **Add Point**.
5. What is the computed RH of this point? Is it close to saturation?

### Exercise 2.4 -- Add a Point Using Tdb + W
1. Select **Tdb + W (lb/lb)**.
2. Enter Tdb = **80** and W = **0.012**.
3. Label it **"Test-W"**.
4. Click **Add Point**.
5. Expand the card. What is the RH? What is the humidity ratio in grains
   per pound (W_display)?

### Exercise 2.5 -- Add a Point Using Tdb + h
1. Select **Tdb + h**.
2. Enter Tdb = **70** and h = **28**.
3. Label it **"Test-h"**.
4. Click **Add Point**.

### Exercise 2.6 -- Click-to-Add
1. Click somewhere on the chart where dry-bulb is approximately 85°F.
2. Notice that the State Point form auto-fills with Tdb + W values.
3. Change the label to **"Clicked"** and click **Add Point**.

### Exercise 2.7 -- Select and Delete
1. Click on the "Test-W" card in the State Points list to select it. Notice
   the highlight ring.
2. Press the **Delete** key. Verify it is removed.
3. Click on the "Test-h" marker directly on the chart. Verify it becomes
   selected.
4. Press **Escape** to deselect.

### Exercise 2.8 -- Clear All
1. Verify you have multiple points in the list.
2. Click the **Clear all** link at the bottom of the State Points list.
3. Verify all points are removed from both the list and the chart.

---

## Exercise Set 3: Psychrometric Processes

**Objective:** Model each of the 12 process types individually.

### Exercise 3.1 -- Sensible Heating (Target Tdb)
1. Select process type **Sensible Heating**.
2. Enter start point: Tdb = **55**, RH = **90** (using Tdb + RH).
3. Set mode to **Target Tdb** and enter target = **75**.
4. Click **Add Process**.
5. Observe the horizontal line on the chart (humidity ratio stays constant).
6. Expand the process card. What is the delta T?

### Exercise 3.2 -- Sensible Cooling (Delta T)
1. Select **Sensible Cooling**.
2. Start: Tdb = **90**, RH = **40**.
3. Mode: **Delta T**, value = **15**.
4. Click **Add Process**.
5. What is the end-point dry-bulb? Verify the humidity ratio is the same at
   start and end.

### Exercise 3.3 -- Sensible Heating (Q + Airflow)
1. Select **Sensible Heating**.
2. Start: Tdb = **55**, RH = **95**.
3. Mode: **Q + Airflow**.
4. Enter Q = **36000** BTU/hr and Airflow = **1000** CFM.
5. Click **Add Process**.
6. Expand the card. What target Tdb did the process reach?

### Exercise 3.4 -- Cooling & Dehumidification (Forward)
1. Select **Cooling & Dehumidification**.
2. Start: Tdb = **80**, RH = **50**.
3. Mode: **Forward (ADP + BF)**.
4. ADP Tdb = **45**, BF = **0.15**.
5. Click **Add Process**.
6. Observe the curved path on the chart. Expand the card to see the ADP,
   BF, Qs, Ql, Qt, and SHR.

### Exercise 3.5 -- Cooling & Dehumidification (Reverse)
1. Select **Cooling & Dehumidification**.
2. Start: Tdb = **80**, RH = **50**.
3. Mode: **Reverse (Leaving conditions)**.
4. Leaving Tdb = **55**, Leaving RH = **90**.
5. Click **Add Process**.
6. What ADP and bypass factor were computed?

### Exercise 3.6 -- Adiabatic Mixing
1. Select **Adiabatic Mixing**.
2. Start (Stream 1): Tdb = **75**, RH = **50**.
3. Stream 2: Tdb = **95**, RH = **40** (using Tdb + RH).
4. Stream 1 fraction = **0.7** (70% return air, 30% outdoor air).
5. Click **Add Process**.
6. Expand the card. What is the mixed-air dry-bulb temperature?

### Exercise 3.7 -- Steam Humidification (Target RH)
1. Select **Steam Humidification**.
2. Start: Tdb = **70**, RH = **20**.
3. Mode: **Target RH**, target = **50**.
4. Click **Add Process**.
5. The path should be nearly vertical (Tdb barely changes). Verify this on
   the chart.

### Exercise 3.8 -- Steam Humidification (Target W)
1. Select **Steam Humidification**.
2. Start: Tdb = **70**, RH = **20**.
3. Mode: **Target W**, target = **0.006** lb/lb.
4. Click **Add Process**.

### Exercise 3.9 -- Adiabatic Humidification (Effectiveness)
1. Select **Adiabatic Humidification**.
2. Start: Tdb = **85**, RH = **20**.
3. Mode: **Effectiveness**, value = **0.80**.
4. Click **Add Process**.
5. The path follows the constant wet-bulb line. Expand the card to see the
   start and end RH values.

### Exercise 3.10 -- Adiabatic Humidification (Target RH)
1. Select **Adiabatic Humidification**.
2. Start: Tdb = **85**, RH = **20**.
3. Mode: **Target RH**, target = **60**.
4. Click **Add Process**.

### Exercise 3.11 -- Heated Water Spray
1. Select **Heated Water Spray**.
2. Start: Tdb = **65**, RH = **30**.
3. Water temperature = **120** °F, Effectiveness = **0.70**.
4. Click **Add Process**.
5. Note that the path slopes upward-right (both Tdb and W increase) because
   the water temperature is above the air wet-bulb.

### Exercise 3.12 -- Direct Evaporative Cooling
1. Select **Direct Evaporative**.
2. Start: Tdb = **100**, RH = **15**.
3. Effectiveness = **0.85**.
4. Click **Add Process**.
5. What is the end-point dry-bulb? What is the end-point RH?

### Exercise 3.13 -- Indirect Evaporative Cooling
1. Select **Indirect Evaporative**.
2. Start: Tdb = **100**, RH = **15**.
3. Effectiveness = **0.70**.
4. Click **Add Process**.
5. How does this process differ from direct evaporative on the chart? (Hint:
   humidity ratio should remain constant.)

### Exercise 3.14 -- Indirect-Direct Evaporative (Two-Stage)
1. Select **Indirect-Direct (Two-Stage)**.
2. Start: Tdb = **105**, RH = **10**.
3. IEC Effectiveness = **0.60**, DEC Effectiveness = **0.80**.
4. Click **Add Process**.
5. Expand the card. What is the intermediate dry-bulb (after the indirect
   stage)? What is the total delta Tdb?

### Exercise 3.15 -- Chemical Dehumidification (Target W)
1. Select **Chemical Dehumidification**.
2. Start: Tdb = **80**, RH = **70**.
3. Mode: **Target W**, target = **0.008** lb/lb.
4. Click **Add Process**.
5. The process follows a constant-enthalpy path. What happened to the
   dry-bulb temperature?

### Exercise 3.16 -- Chemical Dehumidification (Target RH)
1. Select **Chemical Dehumidification**.
2. Start: Tdb = **80**, RH = **70**.
3. Mode: **Target RH**, target = **30**.
4. Click **Add Process**.

### Exercise 3.17 -- Sensible Reheat
1. Select **Sensible Reheat**.
2. Start: Tdb = **52**, RH = **95**.
3. Mode: **Target Tdb**, target = **55**.
4. Click **Add Process**.
5. This is typically the final step after cooling & dehumidification when the
   coil leaving temperature is too low for comfort.

---

## Exercise Set 4: Process Chaining

**Objective:** Build a multi-step air handling sequence using process chaining.

### Exercise 4.1 -- Mixed Air + Cooling + Reheat
1. **Clear all** existing processes from the Processes list.
2. Add a **Sensible Heating** process:
   - Start: Tdb = **75**, RH = **50** (room return air).
   - Mode: Target Tdb = **75** (this is a no-op just to establish the point).
   - Actually, let's start with **Adiabatic Mixing**:
     - Stream 1 (return): Tdb = **75**, RH = **50**.
     - Stream 2 (outdoor): Tdb = **95**, Twb = **78** (use Tdb + Twb pair).
     - Stream 1 fraction = **0.70**.
   - Click **Add Process**.
3. Check the **"Chain from Process 1 end point"** checkbox.
4. Select **Cooling & Dehumidification** (Forward).
5. ADP = **45**, BF = **0.12**.
6. Click **Add Process**.
7. Check the **"Chain from Process 2 end point"** checkbox.
8. Select **Sensible Reheat**.
9. Mode: Target Tdb = **55**.
10. Click **Add Process**.
11. Observe all three processes drawn sequentially on the chart with chain
    connectors in the process list.

### Exercise 4.2 -- Evaporative Cooling Chain
1. Clear all processes.
2. Start with **Indirect Evaporative**: Tdb = **110**, RH = **8%**,
   effectiveness = **0.65**.
3. Chain **Direct Evaporative** from the end of process 1, effectiveness =
   **0.85**.
4. Observe the two-step cooling path: first a horizontal drop (indirect),
   then a slope toward the wet-bulb (direct).

---

## Exercise Set 5: Coil Analysis

**Objective:** Perform forward and reverse coil analysis with optional
airflow and water temperature inputs.

### Exercise 5.1 -- Forward Coil Analysis
1. Scroll to the **Coil Analysis** section.
2. Mode: **Forward (ADP + BF)**.
3. Entering air: Tdb = **80**, RH = **50** (Tdb + RH pair).
4. ADP Tdb = **45**, BF = **0.15**.
5. Click **Analyze Coil**.
6. Review the results: What is the leaving Tdb? The bypass factor? The
   contact factor? The SHR?
7. Observe the cyan coil path on the chart, the entering/leaving markers,
   and the ADP star on the saturation curve.

### Exercise 5.2 -- Forward Coil with Airflow
1. Keep the same entering conditions and ADP/BF from Exercise 5.1.
2. Enter an airflow of **2000** CFM.
3. Click **Analyze Coil** again.
4. The loads (Qs, Ql, Qt) should now be in BTU/hr instead of per-unit-mass.
   Record the three load values.

### Exercise 5.3 -- Forward Coil with Water Temperatures
1. Keep everything from Exercise 5.2.
2. Enter water entering temp = **42** °F and water leaving temp = **56** °F.
3. Click **Analyze Coil**.
4. A GPM value should appear in the results. What is it?

### Exercise 5.4 -- Reverse Coil Analysis
1. Change mode to **Reverse (Leaving conditions)**.
2. Entering air: Tdb = **80**, RH = **50**.
3. Leaving air: Tdb = **55**, RH = **90** (Tdb + RH pair).
4. Click **Analyze Coil**.
5. What ADP and bypass factor were computed? Compare to the forward analysis.

---

## Exercise Set 6: SHR Tools

**Objective:** Plot SHR lines and perform GSHR/ESHR analysis.

### Exercise 6.1 -- Plot a Room SHR Line
1. Scroll to the **SHR Tools** section.
2. In the **Room SHR Line** sub-panel:
   - Room state: Tdb = **75**, RH = **50** (Tdb + RH).
   - SHR = **0.75**.
3. Click **Add SHR Line**.
4. Observe the dashed red line on the chart extending from the room point
   down to the saturation curve.
5. In the SHR lines list, note the ADP temperature where the line
   intersects the saturation curve.

### Exercise 6.2 -- Plot Multiple SHR Lines
1. Add another SHR line: same room point (75°F, 50% RH), but SHR = **0.85**.
2. Add a third: SHR = **0.65**.
3. Observe how steeper SHR values (lower SHR = more latent) produce steeper
   lines and lower ADP values.

### Exercise 6.3 -- GSHR / ESHR Analysis
1. Expand the **GSHR / ESHR Calculator** by clicking on it.
2. Enter:
   - Room state: Tdb = **75**, RH = **50**.
   - Outdoor air: Tdb = **95**, RH = **40**.
   - Room sensible load Qs = **60000** BTU/hr.
   - Room total load Qt = **80000** BTU/hr.
   - OA fraction = **0.30**.
   - Total airflow = **3000** CFM.
   - BF for ESHR = **0.10** (optional).
3. Click **Calculate GSHR**.
4. In the results panel, record: Room SHR, GSHR, ESHR.
5. On the chart, identify the three lines (Room SHR -- dashed, GSHR --
   dash-dot, ESHR -- dotted) and the mixed air triangle marker.
6. Note the ADP values for each SHR line. Which SHR has the lowest ADP?

---

## Exercise Set 7: Airflow Calculator

**Objective:** Use the airflow/load calculator and condensation checker.

### Exercise 7.1 -- Solve for Q (Sensible)
1. Scroll to the **Airflow Calculator** section.
2. Load type: **Sensible (Qs)**.
3. Solve for: **Solve for Q**.
4. Enter airflow = **1500** CFM and delta T = **20** °F.
5. Click **Calculate**.
6. Record the calculated Q, the C factor, and the air density.
7. Verify the formula shown matches Q = C * CFM * delta_T.

### Exercise 7.2 -- Solve for Airflow (Sensible)
1. Keep load type as Sensible.
2. Change to **Solve for Airflow**.
3. Enter Q = **36000** BTU/hr and delta T = **20** °F.
4. Click **Calculate**.
5. What airflow (CFM) is required?

### Exercise 7.3 -- Solve for Delta (Sensible)
1. Change to **Solve for Delta**.
2. Enter Q = **36000** BTU/hr and airflow = **1500** CFM.
3. Click **Calculate**.
4. What temperature difference is computed?

### Exercise 7.4 -- Latent Load Calculation
1. Change load type to **Latent (Ql)**.
2. Solve for: **Solve for Q**.
3. Enter airflow = **2000** CFM and delta W = **0.005** lb/lb.
4. Click **Calculate**.
5. Record the latent heat load Q.

### Exercise 7.5 -- Total Load Calculation
1. Change load type to **Total (Qt)**.
2. Solve for: **Solve for Q**.
3. Enter airflow = **2000** CFM and delta h = **10** BTU/lb.
4. Click **Calculate**.

### Exercise 7.6 -- Auto-Fill from Process
1. First, add a **Sensible Heating** process: start Tdb = **55**, RH = **90**,
   target Tdb = **75**.
2. Return to the Airflow Calculator. Set load type = Sensible, mode = Solve
   for Q.
3. Use the **"Auto-fill delta from process"** dropdown and select the
   sensible heating process.
4. Verify that the delta T field auto-fills with 20 (the difference between
   75 and 55).
5. Enter airflow = **1200** CFM and click **Calculate**.

### Exercise 7.7 -- Condensation Checker
1. Expand the **Condensation Checker** panel.
2. Enter surface temperature = **50** °F.
3. Air state: Tdb = **75**, RH = **60** (Tdb + RH).
4. Click **Check Condensation**.
5. Does condensation occur? What is the dew point? What is the margin?

### Exercise 7.8 -- Condensation Checker (Safe)
1. Change the surface temperature to **65** °F.
2. Keep the same air state (75°F, 60% RH).
3. Click **Check Condensation**.
4. This time condensation should NOT occur. What is the margin?

### Exercise 7.9 -- Auto-Fill Condensation from State Point
1. Ensure you have at least one state point (add one at 75°F / 50% RH if
   needed).
2. In the condensation checker, use the **"Auto-fill from state point"**
   dropdown to select it.
3. Verify the air state fields populate automatically.
4. Enter a surface temperature and check.

---

## Exercise Set 8: AHU Wizard

**Objective:** Use the step-by-step AHU wizard to design an air handling
unit.

### Exercise 8.1 -- Mixed Air AHU
1. Scroll to the **AHU Wizard** section.
2. Step 1 -- AHU Type: select **Mixed Air**.
3. Step 2 -- Outside Air: Tdb = **95**, Twb = **78**.
4. Step 3 -- Return Air: Tdb = **75**, RH = **50**.
5. Step 4 -- Mixing: OA fraction = **0.30**.
6. Step 5 -- Supply Target: Supply Tdb = **55**. Leave Supply RH and Qs
   room blank.
7. Step 6 -- Review and click **Calculate**.
8. Examine the results:
   - What is the mixed air temperature?
   - What are the cooling loads (Qs, Ql, Qt)?
   - Does the system need reheat?
   - What is the SHR?

### Exercise 8.2 -- Apply AHU Results to Chart
1. After completing Exercise 8.1, click **"Apply to Chart"**.
2. Observe all the state points (OA, RA, Mix, Coil Leaving, Supply) and
   process paths that appear on the main chart.

### Exercise 8.3 -- 100% Outside Air AHU
1. Click **Clear** on the AHU Wizard to start over.
2. Step 1: select **100% Outside Air**.
3. Step 2: Tdb = **95**, Twb = **78**.
4. (Steps 3 and 4 are skipped for full OA systems.)
5. Step 3 (Supply Target): Supply Tdb = **55**.
6. Calculate. Compare the cooling loads to the mixed-air system. Which
   requires more cooling?

### Exercise 8.4 -- AHU Wizard with Airflow Sizing
1. Clear and start a new Mixed Air wizard.
2. OA: Tdb = **95**, Twb = **78**.
3. RA: Tdb = **75**, RH = **50**.
4. OA fraction = **0.25**.
5. Supply Tdb = **55**.
6. Room sensible load Qs = **120000** BTU/hr.
7. Calculate.
8. The results should include a supply airflow (CFM). Record it.

---

## Exercise Set 9: ASHRAE Design Days

**Objective:** Look up and overlay design day conditions for a location.

### Exercise 9.1 -- Search and Load
1. Scroll to the **ASHRAE Design Days** section.
2. Type "Phoenix" in the search box.
3. Select **Phoenix, AZ** from the dropdown.
4. Click **Load Conditions**.
5. How many design conditions were loaded?
6. What is the 0.4% cooling dry-bulb temperature?

### Exercise 9.2 -- Observe Chart Overlay
1. After loading Phoenix design conditions, look at the chart.
2. Identify the orange upward-triangle markers (cooling conditions) and any
   blue downward-triangle markers (heating conditions).
3. Hover over a cooling design point to see its properties.

### Exercise 9.3 -- Use Design Day in AHU Wizard
1. With Phoenix design days loaded, open the AHU Wizard.
2. On the Outside Air step, click **"Pre-fill from design day data"**.
3. Verify the OA Tdb and Twb fields auto-fill with the cooling design day
   values.

### Exercise 9.4 -- Clear and Try Another City
1. Click **Clear** on the design day panel.
2. Search for "Chicago" and load its design conditions.
3. Compare Chicago's cooling design conditions to Phoenix.

---

## Exercise Set 10: TMY Weather Data

**Objective:** Upload and visualize TMY weather data.

### Exercise 10.1 -- Upload a TMY File
1. Scroll to the **TMY Weather Data** section.
2. Click **"Upload Weather File (CSV / EPW)"**.
3. Select an EPW or CSV weather file from your computer. (EPW files can be
   downloaded from the EnergyPlus weather data site.)
4. Wait for the file to process. The total number of hours should appear.

### Exercise 10.2 -- Scatter Mode
1. After uploading, ensure the display mode is set to **Scatter**.
2. Observe the 8,760 dots on the chart. Dots are color-coded by month.
3. Identify the cluster of summer conditions (warm, higher humidity) and
   winter conditions (cool, lower humidity).

### Exercise 10.3 -- Heatmap Mode
1. Switch the display to **Heatmap**.
2. The chart now shows a colored grid where brighter cells represent more
   hours at that temperature/humidity combination.
3. Identify the most frequent conditions (brightest area).

### Exercise 10.4 -- Clear TMY
1. Click **Clear TMY Data** and verify the overlay is removed.

---

## Exercise Set 11: Chart Interactions & Layers

**Objective:** Practice chart interaction features and layer visibility
controls.

### Exercise 11.1 -- Layer Toggles
1. Click the **Layers** button in the top-left corner of the chart.
2. Uncheck **Enthalpy Lines**. Observe the yellow dash-dot lines disappear.
3. Uncheck **Volume Lines**. Observe the purple dotted lines disappear.
4. Re-check both. Confirm they reappear.
5. Uncheck **RH Lines** -- only the saturation curve (100% RH) remains.
   Re-check it.

### Exercise 11.2 -- Toggle Data Layers
1. Add two state points and one process.
2. Uncheck **State Points** in the Layers panel. The markers disappear.
3. Uncheck **Processes**. The process line disappears.
4. Re-check both.

### Exercise 11.3 -- Hover Readout
1. Slowly move your cursor across the chart from left (cool) to right (warm).
2. Watch the floating tooltip update in real-time.
3. At approximately 75°F and 50 gr/lb, note the RH, Twb, Tdp, h, and v
   values.

### Exercise 11.4 -- Resize and Collapse Sidebar
1. Grab the divider handle between the chart and sidebar. Drag it left to
   make the sidebar wider.
2. Drag it right to make the sidebar narrower.
3. Click the arrow button on the divider to collapse the sidebar entirely.
   The chart expands to full width.
4. Click the arrow again to restore the sidebar.

---

## Exercise Set 12: Project Management & Export

**Objective:** Save, load, and export projects.

### Exercise 12.1 -- Save a Project
1. Add at least two state points and one process.
2. Rename the project to "Exercise Project".
3. Click **Save** (or press `Ctrl+S`).
4. A `.json` file should download. Locate it in your downloads folder.

### Exercise 12.2 -- Clear and Load
1. Click the title and rename to "Cleared".
2. In the State Points list, click **Clear all**.
3. In the Processes list, click **Clear all**.
4. Now click **Load** and select the `Exercise_Project.json` file you saved.
5. Verify the project title, state points, and processes are restored.

### Exercise 12.3 -- Export as PNG
1. Click **Export > Chart as PNG**.
2. A PNG image should download. Open it and verify it matches the chart.

### Exercise 12.4 -- Export as SVG
1. Click **Export > Chart as SVG**.
2. Open the SVG in a browser or vector editor.

### Exercise 12.5 -- Export as CSV
1. Click **Export > Data as CSV**.
2. Open the CSV in a spreadsheet application.
3. Verify it contains state point properties and process data.

### Exercise 12.6 -- Export as PDF
1. Click **Export > PDF Report**.
2. Wait for the report to generate (a toast notification appears).
3. Open the PDF. It should contain the chart image, state point tables, and
   process details.

### Exercise 12.7 -- Undo and Redo
1. Add a state point (75°F, 50% RH, label "UndoTest").
2. Press `Ctrl+Z` (undo). The point should disappear.
3. Press `Ctrl+Shift+Z` (redo). The point should reappear.
4. Repeat undo/redo several times.

---

## Exercise Set 13: Unit System & Pressure

**Objective:** Switch between IP and SI units and adjust barometric pressure.

### Exercise 13.1 -- Switch to SI
1. Click the unit toggle button to switch from **IP** to **SI**.
2. Observe that:
   - The chart x-axis now reads "Dry-Bulb Temperature (°C)".
   - The y-axis now reads "Humidity Ratio (g/kg)".
   - The pressure field shows 101325 Pa.
   - The altitude field is 0 m.
3. Add a state point: Tdb = **25** °C, RH = **50**. Expand it and record the
   properties in SI units.

### Exercise 13.2 -- SI Process
1. While in SI mode, add a **Sensible Heating** process:
   - Start: Tdb = **12**, RH = **95**.
   - Target Tdb = **24**.
2. Verify the chart shows the process correctly in °C.

### Exercise 13.3 -- Switch Back to IP
1. Switch back to **IP**. Note that existing processes are cleared (since they
   were computed in SI). State points defined in SI remain in the list but the
   chart regenerates at IP pressure.

### Exercise 13.4 -- Altitude Adjustment
1. In IP mode, enter altitude = **5280** ft (Denver, CO) and press Enter.
2. The pressure should update to approximately **12.23 psia** (not 14.696).
3. Add a state point: Tdb = **75**, RH = **50**. Compare its enthalpy and
   specific volume to the same point at sea level.

### Exercise 13.5 -- Direct Pressure Entry
1. Change the pressure directly to **13.0** psia by typing in the P field and
   pressing Enter.
2. The chart regenerates. Note the saturation curve shifts slightly.

---

## Exercise Set 14: Integrated Design Problem

**Objective:** Combine multiple features to solve a realistic HVAC design
problem.

### Scenario

You are designing an air handling unit for a commercial office building in
Atlanta, GA. The design conditions are:

- **Outdoor summer design:** Tdb = 92°F, coincident Twb = 74°F
- **Room conditions:** 75°F, 50% RH
- **Outside air fraction:** 25%
- **Room sensible load:** 150,000 BTU/hr
- **Room total load:** 200,000 BTU/hr
- **Supply air temperature:** 55°F

### Exercise 14.1 -- Set Up Design Conditions
1. Start a new project. Name it "Atlanta Office AHU".
2. Ensure IP units and standard sea-level pressure.
3. Add a state point for outdoor air: Tdb = **92**, Twb = **74** (use Tdb +
   Twb). Label it **"OA Design"**.
4. Add a state point for room conditions: Tdb = **75**, RH = **50**. Label it
   **"Room"**.

### Exercise 14.2 -- Look Up Design Day
1. Search for "Atlanta" in the ASHRAE Design Days panel.
2. Load the design conditions.
3. Compare the loaded cooling design day Tdb to your manual entry (92°F).
4. Note any differences.

### Exercise 14.3 -- GSHR Analysis
1. Open the GSHR/ESHR calculator.
2. Enter:
   - Room: 75°F, 50% RH.
   - OA: 92°F, Twb = 74°F (use Tdb + Twb pair).
   - Qs room = 150000, Qt room = 200000.
   - OA fraction = 0.25.
   - Total airflow = 5000 CFM (initial estimate).
   - BF = 0.10.
3. Calculate GSHR.
4. Record: Room SHR, GSHR, ESHR, and the ADP for each.

### Exercise 14.4 -- AHU Wizard
1. Run the AHU Wizard with:
   - Mixed Air type.
   - OA: 92°F, Twb = 74°F.
   - RA: 75°F, 50% RH.
   - OA fraction: 0.25.
   - Supply Tdb: 55°F.
   - Room Qs: 150000 BTU/hr.
2. What supply airflow does the wizard calculate?
3. Does the system need reheat?
4. Apply the results to the chart.

### Exercise 14.5 -- Build the AHU Manually with Process Chaining
1. Clear all processes.
2. Step 1: **Adiabatic Mixing** -- RA (75°F, 50%) + OA (92°F, Twb 74°F),
   stream 1 fraction = 0.75.
3. Step 2: Chain **Cooling & Dehumidification** (Forward) -- pick an ADP
   based on the GSHR analysis (e.g., the ESHR ADP from Exercise 14.3) and
   a BF = 0.10.
4. Step 3: Chain **Sensible Reheat** to reach 55°F.
5. Observe the complete AHU process chain on the chart.

### Exercise 14.6 -- Coil Analysis
1. Perform a **Forward Coil Analysis** with:
   - Entering air = the mixed air state (Tdb from mixing, RH from mixing).
   - ADP = the value from Exercise 14.3.
   - BF = 0.10.
   - Airflow = the supply CFM from Exercise 14.4.
   - Water temps: entering = 42°F, leaving = 56°F.
2. Record the total cooling load (Qt) in BTU/hr and the water GPM.

### Exercise 14.7 -- Airflow Verification
1. Use the Airflow Calculator with:
   - Load type: Sensible.
   - Q = 150000 BTU/hr.
   - Delta T = 20°F (75°F room - 55°F supply).
2. Solve for airflow. Does the result match the AHU wizard's supply CFM?

### Exercise 14.8 -- Condensation Check
1. Check whether a duct surface at 50°F will condense moisture from the
   room air (75°F, 50% RH).
2. What about from the supply air (55°F, ~90% RH)?

### Exercise 14.9 -- Save and Export
1. Save the project as JSON.
2. Export the chart as PNG.
3. Export a PDF report.
4. Export the data as CSV.

---

## Answers & Expected Results

Approximate answers are provided below. Due to rounding in psychrometric
calculations, your values may differ slightly.

### Exercise 2.2
- RH: ~51%, W: ~99 gr/lb, h: ~41.6 BTU/lb, Tdp: ~72.6°F

### Exercise 2.3
- RH: ~91-93% (close to saturation)

### Exercise 2.4
- RH: ~57-59%, W_display: ~84 gr/lb

### Exercise 3.1
- Delta T: 20°F

### Exercise 3.2
- End Tdb: 75°F. Humidity ratio is unchanged (sensible process).

### Exercise 3.6
- Mixed Tdb: ~81°F (weighted average: 0.7 * 75 + 0.3 * 95 = 81)

### Exercise 3.12
- End Tdb: ~66-68°F, End RH: ~75-80% (depends on entering wet-bulb)

### Exercise 3.13
- Humidity ratio is constant (horizontal move on chart), unlike direct
  evaporative which increases W.

### Exercise 3.15
- Dry-bulb temperature increased (chemical dehumidification is exothermic
  along constant enthalpy).

### Exercise 5.1
- Leaving Tdb: ~49.8°F, BF: 0.15, CF: 0.85, SHR: ~0.68

### Exercise 6.3
- Room SHR: 0.75 (150000/200000)
- GSHR and ESHR will depend on the mixed air condition
- The ESHR ADP will be the lowest (most demanding)

### Exercise 7.1
- Q: approximately 32,400 BTU/hr (using C ~ 1.08 for standard air)

### Exercise 7.2
- Airflow: approximately 1,667 CFM

### Exercise 7.7
- Dew point of 75°F/60% air: ~60.3°F. Surface at 50°F is below the dew
  point, so condensation WILL occur. Margin: ~-10.3°F.

### Exercise 7.8
- Surface at 65°F, dew point ~60.3°F. No condensation. Margin: ~+4.7°F.

### Exercise 8.1
- Mixed Tdb: ~81°F (0.7 * 75 + 0.3 * 95)
- Reheat: depends on whether coil leaving is below 55°F

### Exercise 13.4
- At 5280 ft / ~12.23 psia: enthalpy is similar but specific volume is
  larger (air is less dense at altitude).

### Exercise 14.4
- Supply airflow: approximately 6,900-7,000 CFM
  (150000 / (1.08 * 20) = ~6,944 CFM)

### Exercise 14.7
- Airflow = 150000 / (1.08 * 20) = ~6,944 CFM. Should match the wizard.
