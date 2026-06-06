# REQUIREMENTS — Phase 1 Real-City Simulation

> **Owner of this doc:** Person 1 (Simulation Core + Infra)  
> **Folders I own:** `simulation/`, `infra/`  
> **City:** New Delhi — Rajiv Chowk, 3–5 km radius (28.6328° N, 77.2197° E)  
> **Python:** 3.12 (pinned — osmnx/geopandas don't support 3.14)

---

## Current State of My Folders

### `simulation/` — What I've Already Built

| File | Lines | What It Does |
|---|---|---|
| `simulation/simulation/engine.py` | 310 | Mesa-backed `UrbanModel` + `MesaSimEngine` adapter. Tick loop, event dispatch, snapshot generation, 10×10 grid aggregation. |
| `simulation/simulation/network.py` | 484 | `MultiModalNetwork` — Delhi (Rajiv Chowk) 10×10 grid with roads, Yellow/Blue metro lines (DMRC), CP outer ring bus loop. Dijkstra routing, BPR congestion, routing cache. |
| `simulation/simulation/agents.py` | 353 | `CitizenAgent` — MNL mode choice, memory, schedule adaptation, advance-commute stepping. |
| `simulation/simulation/metrics.py` | 109 | `calculate_metrics()` — mode share, avg commute time, congestion index, metro load. |
| `simulation/simulation/__init__.py` | 8 | Public exports. |
| `simulation/tests/test_simulation.py` | 229 | 7 tests: init, stepping, events, determinism, routing cache, multi-modal routing, BPR calibration. |
| `simulation/pyproject.toml` | 24 | Deps: `mesa>=2.2`, `numpy`, `networkx`, `pandas`. |

> **Status:** Grid is now centered on Delhi Rajiv Chowk (28.6328, 77.2197) with Yellow/Blue DMRC metro lines. Still synthetic grid — will be swapped for real OSM data when data pipeline outputs are available.

### `infra/` — What Exists

| File | What |
|---|---|
| `infra/CLAUDE.md` | Agent guidance — Docker, CI/CD, K8s, Terraform scope |
| `infra/rule.md` | Git branch rules |
| `infra/agents/rules/rule.md` | AI agent rules for infra |

> **Status:** Empty scaffold. CI/CD and deployment are Phase 2 concerns per PROJECT_SPEC §13.

---

## What I Need From Each Role (Precise Deliverables)

---

### FROM SUB-04 — Data Engineering (Person 4)

> **Priority: 🔴 CRITICAL — I am blocked until these files exist.**

#### File 1: `data/processed_data/weather_delhi.csv`
- **Format:** CSV
- **Content:** Daily rainfall + temperature for Delhi, at least one monsoon season (Jun–Sep)
- **Schema:** `date, rainfall_mm, temp_max_c, temp_min_c, humidity_pct`
- **Why I need it:** To drive Scenario A (Monsoon Stress Test). My engine currently has `weather_rain_intensity` as a float 0–1; I need a mapping from actual rainfall mm to this intensity.
- **Source:** IMD open data or OpenWeather historical API.

#### File 2: `data/processed_data/synthetic_population.parquet`
- **Format:** Parquet
- **Content:** 5,000 agent records assigned to real OSM node IDs
- **Schema I need:**
```
agent_id          int64       unique
home_node         str         real OSM node ID from nodes.parquet
work_node         str|null    real OSM node ID (null for non-workers/retired)
age               int
income_bracket    int (1-5)
household_id      int
occupation        str         office_executive|student|blue_collar_worker|gig_worker|retired_citizen
has_car           bool
has_bike          bool
has_metro_pass    bool
```
- **Why I need it:** My `UrbanModel._generate_synthetic_population()` currently generates agents randomly. I need a `_load_real_population()` path that reads this fixed file.
- **Status:** Need Person 4 to run `3_generate_population.py` to generate this file using the OSM network.

#### File 3: `data/validation/mode_share_delhi.csv`
- **Format:** CSV
- **Schema:** `mode, share_pct, source, year`
- **Why I need it:** To calibrate agent utility weights so simulated mode share matches reality.

#### File 4: `data/validation/dmrc_ridership.csv`
- **Format:** CSV
- **Schema:** `station, daily_ridership, peak_hour_ridership, source, year`
- **Why I need it:** Validation anchor — is my metro load metric in the right ballpark?

---

### FROM SUB-07 — Research (Person 7)

> **Priority: 🟡 MEDIUM — needed for calibration.**

| # | Deliverable | Why |
|---|---|---|
| 1 | **`research/experiments/anchors.yaml`** — Formal anchor metric definitions | I need to know what values my simulation should hit. |
| 2 | **Calibration feedback** — "Your mode share is X%, real is Y%, adjust β_cost" | I tune utility weights based on their analysis. |

---

### FROM SUB-06 — Frontend (Person 6)

> **Priority: 🟢 LOW — they consume my snapshots, I don't depend on them.**

#### What they need from me (for their reference):
- `Snapshot` object with `grid: list[GridCell]` (lat, lon, density, congestion)
- `AggregateMetrics` with mode_share, avg_commute, metro_load, congestion_index
- WebSocket stream from backend

#### What I need from them:
Nothing for Phase 1. They consume my output.

---

## What I Must Deliver (My Own Checklist)

### `simulation/` Changes for Phase 1

| # | File | Change | Depends On |
|---|---|---|---|
| 1 | `simulation/simulation/engine.py` | Add `_load_real_population(parquet_path)` alongside existing `_generate_synthetic_population()` | SUB-04 file 2 |
| 2 | `simulation/scenarios/baseline_delhi.yaml` | **NEW** — Default scenario config for Delhi | All data files |

### `infra/` — Phase 1 Scope

| # | File | What |
|---|---|---|
| 1 | `docker-compose.yml` (root) | Already exists. Verify backend + frontend services work together. |
| 2 | `infra/scripts/setup_env.sh` | **NEW** — One-command dev environment setup (create venvs, install deps, run data pipeline) |
| 3 | `.github/workflows/ci.yml` | **NEW** (when ready) — Run `pytest simulation/tests/` on PR |

---

## Python Dependencies — All Roles

### `simulation/requirements.txt` (my folder)
```txt
# Core simulation
mesa>=2.2.0
numpy>=1.24.0
networkx>=3.2
pandas>=2.0.0

# Real data loading (Phase 1)
osmnx>=1.9.0
geopandas>=0.14
pyarrow>=15.0

# Dev
pytest>=8.0
black>=24.0
ruff>=0.5
mypy>=1.10
```

### `data/requirements.txt` (Person 4 — for reference)
```txt
osmnx>=1.9.0
geopandas>=0.14
pandas>=2.1
shapely>=2.0
networkx>=3.2
pyarrow>=15.0
requests>=2.31
```

### `ai/requirements.txt` (Person 2 — for reference)
```txt
numpy>=1.26
pandas>=2.1
scipy>=1.11
pyarrow>=15.0
# Dev
pytest>=8.0
black>=24.0
ruff>=0.5
mypy>=1.10
```

### `backend/requirements.txt` (Person 5 — for reference)
```txt
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.7
pydantic-settings>=2.3
websockets>=12.0
# Dev
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27
ruff>=0.5
```

### `frontend/package.json` additions (Person 6 — for reference)
```json
{
  "dependencies": {
    "maplibre-gl": "^4.0.0",
    "chart.js": "^4.4.0"
  }
}
```

### `research/requirements.txt` (Person 7 — for reference)
```txt
jupyter>=1.0
matplotlib>=3.8
pandas>=2.1
pyarrow>=15.0
geopandas>=0.14
```

---

## Environment Setup

```bash
# Python 3.12 is required (osmnx has no wheels for 3.14)
# After installing Python 3.12:

# Simulation (my folder)
cd simulation
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
pytest tests/

# Verify
python -c "import mesa; import networkx; print('simulation deps OK')"
```

---

## Dependency Graph — Who Blocks Whom

```
DATA ENGINEER (Person 4)
  │
  ├─ weather_delhi.csv ────► ME (monsoon scenario driver)
  ├─ synthetic_population.parquet ► ME (engine._load_real_population)
  └─ validation CSVs ──────► RESEARCH (Person 7) ──► ME (calibration feedback)

ME (Simulation Core)
  └─ Snapshot stream ──────► BACKEND ──► FRONTEND
```
