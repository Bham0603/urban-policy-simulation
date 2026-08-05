# REQUIREMENTS — Phase 2 & Future Scopes Simulation

> **Owner of this doc:** Person 1 (Simulation Core + Infra)  
> **Folders I own:** `simulation/`, `infra/`  
> **City:** New Delhi — Rajiv Chowk, 3–5 km radius (28.6328° N, 77.2197° E)  
> **Python:** 3.12 (pinned — osmnx/geopandas don't support 3.14)

---

## Current State of My Folders

### `simulation/` — What I've Already Built (Phase 1 Complete)

| File | Lines | What It Does |
|---|---|---|
| `simulation/simulation/engine.py` | ~890 | Mesa-backed `UrbanModel` + `MesaSimEngine`. Tick loop, event dispatch, snapshot generation. **Now loads real OSM `synthetic_population.parquet` and spawns economic agents.** |
| `simulation/simulation/network.py` | ~850 | `MultiModalNetwork` — Delhi 10×10 grid with roads, DMRC metro lines, bus loop. Dijkstra routing, BPR congestion, dynamic routing cache. |
| `simulation/simulation/agents.py` | ~1000 | `CitizenAgent` — MNL mode choice, multi-leg schedules, memory. **Now includes evening discretionary shopping and `ShopChoiceModel` integration.** |
| `simulation/simulation/economic_agents.py`| ~300 | **[NEW]** Mesa wrappers for `StallOwner`, `StoreManager`, `StoreStaff`, and `DeliveryAgent`. Dynamic restocking and rain surge pricing. |
| `simulation/simulation/metrics.py` | ~170 | `calculate_metrics()` — mode share, avg commute, congestion, metro load, **bus load, and AQI estimates**. |
| `simulation/tests/` | 39 Tests | Comprehensive suite covering calibration, determinism, economic agents, and real OSM data loading. **All passing.** |

> **Status:** Base Delhi simulation, real OSM data loading, and AI economic agents are fully integrated. `synthetic_population.parquet` has been successfully generated and loaded.

---

## Detailed Requirements From Other Subsystems (Phase 2 & Integration)

Based on the current progress in the `ai/`, `data/`, `backend/`, and `frontend/` folders, the following are the strict integration requirements necessary for Phase 2 development.

### 1. FROM SUB-04 — Data Engineering (Person 4)
> **Priority: 🔴 CRITICAL — Needed for realistic agent demographics and Phase 2 scenarios.**

**What they have done:**
- `1_download_osm_network.py` generates OSM networks.
- `3_fetch_monsoon_weather.py` generates `weather_delhi.csv`.
- Defined a placeholder for `2_fetch_census_demographics.py`.

**What I need from them in detail:**
1. **Complete Census Demographics Pipeline (`2_fetch_census_demographics.py`)**
   - **Requirement:** I need the synthetic population generator to sample real demographics instead of uniform random distribution.
   - **Details:** The pipeline must output income proxies (PLFS wage brackets) and accurate worker categories for the NCT of Delhi.
2. **Freight & Logistics Data (`data/processed_data/freight_nodes.json`)**
   - **Requirement:** A defined list of hubs for wholesale distribution and last-mile goods movement.
   - **Details:** Must map to existing nodes in `network.graphml`. Will be used to spawn heavy freight agents.
3. **Ride-Hail Historical Data (`data/processed_data/ride_hail_historical.csv`)**
   - **Requirement:** A CSV containing `time_of_day`, `avg_wait_time_mins`, and `surge_multiplier`.
   - **Details:** I need this baseline availability to calibrate the simulation's dynamic ride-hail pricing model.

---

### 2. FROM SUB-02 — Agent Behavior / AI (Person 2)
> **Priority: 🟡 MEDIUM — Needed for expanding agent logic beyond commuting & retail.**

**What they have done:**
- Built comprehensive models for retail agents (`StallOwner`, `StoreManager`), shop choice MNL, and transaction interactions.
- Deferred per-agent heterogeneous utility weights, household joint decisions, and schedule adaptation.

**What I need from them in detail:**
1. **Ride-hail Surge Pricing Algorithm**
   - **Requirement:** A new utility evaluation block inside `sim/agents/mode_choice.py` for Ola/Uber equivalents.
   - **Details:** Needs to include logic that dynamically increases the cost parameter (`surge_multiplier`) based on local demand (number of agents choosing the mode in a tick).
2. **Freight/Logistics Agent Dataclasses**
   - **Requirement:** Core behavioral models for heavy freight drivers.
   - **Details:** Must provide the state logic (e.g., loading, transiting, unloading) so I can port them into Mesa wrappers in `simulation/simulation/economic_agents.py`.
3. **Schedule Adaptation (Deferred Task)**
   - **Requirement:** Implement the "three bad commutes → leave earlier" loop.
   - **Details:** I need the `Agent.adapt_behavior()` method to actually shift departure times based on the `CommuteOutcome` memory.

---

### 3. FROM SUB-05 — Backend & API (Person 5)
> **Priority: 🔴 CRITICAL — Needed to connect my engine to the frontend.**

**What they have done:**
- Built the FastAPI + WebSockets + SQLite app (`backend/`).
- Currently running a stub simulation (`app/sim/fake_engine.py`).

**What I need from them (and what they need from me) in detail:**
1. **Implement the `SimEngine` Protocol**
   - **Requirement:** I (Person 1) need to update `backend/app/sim/adapter.py` to wrap my `MesaSimEngine`.
   - **Details:** Once I implement the protocol, Person 5 must ensure that the backend's `BACKEND_SIM_ENGINE=mesa` toggle correctly instantiates and steps my engine inside their `scenario_manager.py` tick loop.
2. **Event Injection Routing**
   - **Requirement:** Ensure that POST requests to `/events` correctly map to my `MesaSimEngine.queue_event(ev)` method for weather, policy, and infrastructure events.

---

### 4. FROM SUB-06 — Frontend (Person 6)
> **Priority: 🟢 LOW — Needed for visual rendering of Phase 2 features.**

**What they have done:**
- Built a 60 FPS HTML5 Canvas engine with floating map overlays, policies, and charts.
- Parses `Snapshot` objects with grid cells.

**What I need from them in detail:**
1. **Visualizing AQI & Heat-Stress (Heatmaps)**
   - **Requirement:** The UI must consume the `aqi_estimate` and `rain_intensity` metrics from my `AggregateMetrics` payload.
   - **Details:** Render dynamic heatmap overlays on the grid to visually represent smog zones and heat stress.
2. **Distinct Particle Rendering for Economic Agents**
   - **Requirement:** Visually differentiate Delivery Agents and Freight from regular Citizen Commuters.
   - **Details:** My engine will send distinct agent states (e.g., `is_delivery: true`). The canvas engine must render these as different colors or sizes (e.g., orange particles for delivery bikes).

---

### 5. FROM SUB-07 — Research (Person 7)
> **Priority: 🟡 MEDIUM — Needed for validation and calibration.**

**What they have done:**
- Empty placeholder directory (`research/`).

**What I need from them in detail:**
1. **Calibration Anchors (`research/experiments/anchors.yaml`)**
   - **Requirement:** Target metrics for mode share, average commute time, and metro station ridership.
   - **Details:** I cannot finalize the utility weights in the `ModeChoiceModel` without knowing the exact DMRC ridership targets and Delhi mode share percentages we are aiming for.
2. **Heat-Stress Impact Metrics**
   - **Requirement:** Research values on how temperature affects behavior in Delhi.
   - **Details:** Need a function or multiplier detailing how high heat/humidity reduces agent walking speed or increases utility cost for non-AC modes.

---

## Dependency Graph — Phase 2

```
DATA ENGINEER (Person 4)
  │
  ├─ 2_fetch_census_demographics.py ──► ME (Realistic Population)
  ├─ freight_nodes.json ──────────────► ME (Last-mile goods simulation)
  └─ ride_hail_historical.csv ────────► AI & ME (Surge dynamics calibration)

AI (Person 2)
  │
  ├─ Ride-hail Surge Algorithm ───────► ME (Mesa tick loop integration)
  └─ Freight Models & Adaptation ─────► ME (Agent behavior update)

BACKEND (Person 5)
  │
  └─ Adapter Integration ─────────────► ME (Swap fake_engine for MesaSimEngine)

ME (Simulation Core)
  │
  └─ Real Mesa Snapshot stream ───────► BACKEND ──► FRONTEND (Heatmaps, AQI rendering)

RESEARCH (Person 7)
  │
  └─ anchors.yaml ────────────────────► ME (Calibration tuning)
```
