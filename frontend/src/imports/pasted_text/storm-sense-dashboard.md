Create a high-fidelity interactive web dashboard prototype called **StormSense — AI Thunderstorm & Lightning Nowcasting System**.

The product is designed for **IMD/state disaster management control rooms, district administrations, aviation operators, power utilities, and emergency response teams**.

The dashboard predicts thunderstorm and lightning risk **1–3 hours ahead** by combining Doppler Weather Radar, INSAT satellite imagery, lightning sensor data, and NWP weather-model variables.

## Overall Design Direction

Create a professional, realistic **meteorological command-center dashboard**.

Do NOT make it look like a generic SaaS analytics dashboard.

Visual style:

* Dark navy/charcoal control-room interface
* High contrast maps
* Cyan/blue for normal weather information
* Yellow/orange/red for increasing storm severity
* Clean white typography
* Minimal glassmorphism
* Minimal gradients
* Avoid excessive rounded cards
* Avoid unnecessary decorative elements
* Prioritize maps, weather information, alerts, timelines, and actionable information
* Use a modern technical interface similar to professional weather-monitoring software
* Desktop-first responsive layout
* 1440 × 900 primary desktop frame
* Include realistic Indian geographic data and district names
* Use realistic sample data rather than lorem ipsum

The prototype should look convincing enough for an SIH judging demo.

---

# SCREEN 1 — LIVE COMMAND CENTER

Create the primary screen titled:

**StormSense**
**AI Thunderstorm & Lightning Nowcasting**

Top navigation bar:

Left:

* StormSense logo/icon
* "AI Nowcasting"

Center:

* "LIVE"
* Current timestamp: "25 Aug 2026 • 10:42 IST"
* Data refresh: "Updated 2 min ago"

Right:

* Data Status
* System Health indicator
* Notifications
* User profile

Below the navigation, create a horizontal alert banner:

**SEVERE WEATHER WATCH**
"High thunderstorm probability detected over northern Tamil Nadu and adjoining districts."

Include:

* Severity: HIGH
* Forecast window: Next 1–3 hours
* Last updated: 10:40 IST

---

# MAIN MAP AREA

Make the map the largest element on the screen.

Use an India/Tamil Nadu map centered around:

* Chennai
* Tiruvallur
* Kanchipuram
* Chengalpattu
* Ranipet
* Vellore
* Villupuram

Display district boundaries.

Overlay a simulated StormSense probability heatmap.

Use:

* Green = low probability
* Yellow = moderate
* Orange = high
* Red = severe
* Purple/dark red = extreme

Show several storm cells moving toward Chennai.

Each storm cell should contain:

* Storm ID
* Probability %
* Movement direction
* Estimated arrival time

Example:

"Cell S-104"
"Thunderstorm probability: 87%"
"Lightning probability: 72%"
"Moving NE → 32 km/h"
"ETA: 42 min"

Create subtle animated-looking directional arrows showing storm movement.

---

# MAP CONTROLS

Place map controls on the left side:

Layers:

* Storm Probability
* Lightning Density
* Radar Reflectivity
* Satellite IR
* Wind
* District Boundaries

Time selector at bottom of map:

**NOW | +30 MIN | +1 HR | +2 HR | +3 HR**

When selecting +1 HR, the heatmap should represent predicted risk one hour ahead.

Include a small legend:

Storm Probability

* 0–20% Low
* 20–50% Moderate
* 50–75% High
* 75–100% Severe

---

# RIGHT-SIDE ALERT PANEL

Create a vertical panel titled:

**Active Alerts**

Show 3–4 alerts.

Example:

### HIGH

**Lightning Risk**
Chengalpattu District
Probability: 82%
Expected: 11:15–12:30 IST

### HIGH

**Thunderstorm**
Tiruvallur District
Probability: 78%
Expected: 11:00–12:00 IST

### MODERATE

**Thunderstorm Development**
Kanchipuram District
Probability: 61%
Expected: 11:30–13:00 IST

Each alert should have:

* Severity
* Location
* Probability
* Expected time
* "View on map" button

Add a prominent button:

**CREATE ALERT**

---

# BOTTOM INFORMATION BAR

Below the map, create four compact information cards.

### 1. Thunderstorm Risk

**72%**
Next 1 hour

### 2. Lightning Risk

**68%**
Next 1 hour

### 3. Storm Cells

**7 detected**
3 intensifying

### 4. Forecast Confidence

**91%**
Well calibrated

Use small visual indicators/sparklines.

---

# SCREEN 2 — STORM ANALYSIS

Create a second screen accessible by clicking a storm cell.

Title:

**Storm Cell S-104**

Subtitle:

"Detailed AI Analysis"

Large map on the left showing the selected storm cell.

Right-side analysis panel:

### Current Status

**INTENSIFYING**

Thunderstorm Probability
**87%**

Lightning Probability
**72%**

Estimated Intensity
**Severe**

Movement
**NE at 32 km/h**

Estimated Arrival
**42 minutes**

---

# AI EXPLANATION SECTION

Create a section titled:

**Why StormSense is predicting this event**

Show four contributing signals as horizontal bars:

Radar Echo Growth
**92% contribution**

Satellite IR Cooling
**84% contribution**

Lightning Density Increase
**79% contribution**

Atmospheric Instability
**71% contribution**

Below this display:

**AI Interpretation**

"Rapid radar echo growth combined with satellite cloud-top cooling and increasing lightning density indicates strengthening convection."

Do not make this sound like a chatbot response. Make it look like a concise operational explanation.

---

# SCREEN 3 — MULTI-SOURCE DATA FUSION

Create a screen titled:

**Data Fusion**

Subtitle:

"Four real-time sources contributing to the current forecast"

Create four large source cards:

### Doppler Weather Radar

Status: ONLINE

Radar Reflectivity
48 dBZ

Echo Growth
+23% / 15 min

Coverage
84%

### INSAT-3D/3DR

Status: ONLINE

Cloud Top Temperature
−62°C

Cooling Rate
−4.2°C / 15 min

Coverage
100%

### Lightning Sensors

Status: ONLINE

Strikes / 15 min
247

Strike Density
+31%

Coverage
91%

### NWP Model

Status: ONLINE

CAPE
1840 J/kg

CIN
42 J/kg

Wind Shear
18 m/s

Below these cards, create a simple visual showing:

RADAR
+
SATELLITE
+
LIGHTNING
+
NWP
↓
**StormSense Fusion Model**
↓
**3-Hour Risk Forecast**

This should visually communicate the core technical innovation.

---

# SCREEN 4 — 3-HOUR FORECAST

Create a screen titled:

**3-Hour Forecast**

Display a large timeline from:

10:45 → 11:15 → 11:45 → 12:15 → 12:45 → 13:15

Show a graph containing:

* Thunderstorm probability
* Lightning probability

Use different line patterns rather than relying only on color.

Below the graph, show forecast snapshots for:

**NOW**
Low/Moderate/High risk regions

**+1 HOUR**
Storm intensification

**+2 HOURS**
Storm movement

**+3 HOURS**
Storm weakening/movement away

Add a clear statement:

**Peak Risk Window: 11:30–12:30 IST**

---

# SCREEN 5 — ALERT DISPATCH

Create an operational alert screen titled:

**Alert Center**

Show:

Alert Type:

* Thunderstorm
* Lightning
* Severe Weather

Target Area:

* District
* Radius
* Selected coordinates

Severity:

* Advisory
* Watch
* Warning
* Severe Warning

Recipients:
☑ District Disaster Management Authority
☑ Emergency Response Teams
☑ Aviation Operations
☑ Power Utilities
☑ Public Alert System

Message preview:

"StormSense Alert: High probability of severe thunderstorm and lightning activity detected over Chengalpattu district between 11:15–12:30 IST. Probability: 82%. Take appropriate precautions."

Buttons:

**SEND ALERT**

**SCHEDULE**

**CANCEL**

After clicking SEND ALERT, show a confirmation state:

"Alert successfully dispatched"

with timestamp and delivery status.

---

# SCREEN 6 — MODEL PERFORMANCE

Create a screen titled:

**Forecast Performance**

This screen displays evaluation status and dataset metadata:

Evaluation Status:
**Evaluation Pending (Pipeline Proof-of-Concept)**

Training Dataset:
**1 day (2026-08-19), 25 train / 20 val / 0 test samples**

Forecast Lead Horizons:
**+15, +30, +60, +120, +180 min**

Held-out Test Evaluation:
**Pending**

Add a label:

**Prototype Mode**
Pipeline proof-of-concept (not validated for real alerts)

---

# SCREEN 7 — SYSTEM STATUS

Create a screen titled:

**System & Data Health**

Show live status cards:

DWR Radar
● Online
Last update: 10:40

INSAT
● Online
Last update: 10:39

Lightning Network
● Online
Last update: 10:41

NWP
● Online
Latest model: 06Z

Model Inference
● Healthy
Latency: 18 sec

API
● Healthy

Database
● Healthy

Also show:

**Current Forecast Cycle**
10:45 IST

**Next Forecast Cycle**
11:00 IST

**Update Frequency**
Every 15 minutes

---

# INTERACTION FLOW

Make the prototype clickable.

The main demo journey should be:

1. Open Live Command Center
2. See high-risk region on map
3. Click storm cell S-104
4. Open Storm Analysis
5. Show why the model predicts intensification
6. Open Data Fusion
7. Show Radar + Satellite + Lightning + NWP inputs
8. Move to 3-Hour Forecast
9. Show storm progression over time
10. Open Alert Center
11. Create an alert for Chengalpattu
12. Show successful alert dispatch
13. Open Forecast Performance
14. Show POD/FAR/CSI and comparison with single-source models

Use realistic transitions between screens.

---

# DEMO-SPECIFIC DETAILS

The prototype must clearly communicate these five things within the first 30 seconds:

**1. WHAT**
AI-powered thunderstorm and lightning nowcasting.

**2. WHEN**
1–3 hours ahead.

**3. WHERE**
District/grid-level India-focused risk map.

**4. WHY**
Radar + satellite + lightning + NWP fusion.

**5. ACTION**
Generate targeted alerts for authorities and critical stakeholders.

---

# IMPORTANT VISUAL REQUIREMENTS

Use realistic weather-map styling.

Do not use:

* Generic world maps
* Random charts unrelated to weather
* Stock photos
* Cartoon clouds
* Excessive 3D effects
* Giant AI robot graphics
* Generic "AI" illustrations
* Excessive glassmorphism
* Lorem ipsum
* Fake cryptocurrency-style dashboards

The dashboard should feel like an actual **weather intelligence and emergency response system**.

Prioritize:

* Large geographic map
* Storm cells
* Probability heatmaps
* Time progression
* Alert severity
* Meteorological variables
* Data-source status
* Model confidence
* Explainable prediction signals

Use consistent spacing, typography, icons, and component styles across all screens.

Create reusable components for:

* Alert cards
* Data source cards
* Probability badges
* Metric cards
* Map controls
* Timeline controls
* Severity indicators
* Buttons
* Navigation
* Status indicators

Make the final prototype visually polished, technically credible, and suitable for an **SIH 2026 presentation/demo**.
