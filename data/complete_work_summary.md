# Complete Work Summary — `data/` Directory

**Project:** Urban Intelligence Platform (UIP) — Urban Policy Simulation  
**Study Area:** 4 km radius around Rajiv Chowk Metro Station, New Delhi, India (28.6328° N, 77.2197° E)  
**Generated:** 6 June 2026

---

## Table of Contents

1. [Project Setup & Configuration](#1-project-setup--configuration)
2. [Pipelines — Scripts Created](#2-pipelines--scripts-created)
3. [Processed Data — Generated Outputs](#3-processed-data--generated-outputs)
4. [Validation Data — Reference Datasets](#4-validation-data--reference-datasets)
5. [Cache — OSMnx HTTP Cache](#5-cache--osmnx-http-cache)
6. [Raw Data](#6-raw-data)
7. [Documentation & Governance](#7-documentation--governance)
8. [Complete File Inventory](#8-complete-file-inventory)

---

## 1. Project Setup & Configuration

### 1.1 Virtual Environment

- Created a Python virtual environment at `data/venv/` using `python -m venv venv`.
- Activated on Windows via `venv\Scripts\activate`.
- Excluded from version control via `.gitignore`.

### 1.2 Dependencies Installed (`requirements.txt`)

All project dependencies were installed via `pip install -r requirements.txt`:

| Package     | Version  | Purpose                                    |
| ----------- | -------- | ------------------------------------------ |
| `osmnx`     | ≥ 2.1.0  | OpenStreetMap network download & analysis  |
| `geopandas` | ≥ 1.0.0  | Geospatial DataFrames & Parquet export     |
| `pandas`    | ≥ 2.2.0  | Tabular data processing                    |
| `shapely`   | ≥ 2.0.0  | Geometric operations                       |
| `networkx`  | ≥ 3.3    | Graph data structures (bundled with osmnx) |
| `pyarrow`   | ≥ 15.0.0 | Parquet file I/O engine                    |
| `requests`  | ≥ 2.31.0 | HTTP requests for weather API              |

- **Issue resolved:** Identified and fixed a missing `osmnx` module error by installing dependencies.

### 1.3 `.gitignore` Configuration

Configured to exclude:

- Virtual environments (`venv/`, `env/`, `.env`)
- Python bytecode (`__pycache__/`, `*.pyc`)
- Data directories contents (keep directory structure via `.gitkeep`)
  - `raw_data/*` (except `.gitkeep`)
  - `processed_data/*` (except `.gitkeep`)
  - `validation_data/*` (except `.gitkeep`)
- OSMnx cache (`cache/`)
- IDE files (`.vscode/`, `.idea/`)

### 1.4 Study Area Update

- Updated the study area from a **2 km radius** to a **4 km radius** around Rajiv Chowk Metro Station.
- Change reflected in both `README.md` documentation and the `1_download_osm_network.py` pipeline (`RADIUS_M = 4000`).

---

## 2. Pipelines — Scripts Created

All pipeline scripts are located in `data/pipelines/`.

### 2.1 Pipeline 1: `1_download_osm_network.py` ✅ IMPLEMENTED & EXECUTED

**Purpose:** Download and process the drivable street network from OpenStreetMap.

**Configuration:**

- Center: Rajiv Chowk (28.6328° N, 77.2197° E)
- Radius: 4,000 m
- Network type: `drive` (drivable roads only)
- Uses explicit coordinates instead of name query for reproducibility

**Processing Steps (5-step pipeline):**

1. **Download** — Fetched raw graph from OSM (7,236 nodes, 17,985 edges)
2. **Clean** — Retained only the largest strongly-connected component (7,064 nodes, 17,594 edges)
3. **Project** — Projected to local UTM zone for metric measurement accuracy
4. **Save GraphML** — Exported full graph in GraphML format
5. **Save Parquet** — Converted to GeoDataFrame node + edge lists in Parquet format

**Technical Details:**

- Windows console encoding fix (`UTF-8`) to handle Unicode in OSM data
- Mixed-type column handling: object/mixed columns are explicitly string-cast before Parquet serialization to prevent PyArrow data-type mismatch errors
- Error handling with try/except and `sys.exit(1)` on failure

**Outputs Generated:**

- `processed_data/network.graphml` — 7.67 MB
- `processed_data/nodes.parquet` — 0.31 MB (7,064 nodes)
- `processed_data/edges.parquet` — 0.99 MB (17,594 edges)

---

### 2.2 Pipeline 2: `2_fetch_census_demographics.py` ⏳ PLACEHOLDER (NOT YET IMPLEMENTED)

**Purpose:** Download and process 2011 Census of India demographic data for NCT of Delhi.

**Planned Data Tables:**

- **C-13** — Single Year Age Returns → 5-year age cohorts
- **HH-1 / HH-2** — Households by Size → household size probability distribution
- **B-4 (B-series)** — Main Workers by Industrial Category → income proxy distribution

**Planned Processing Steps (all commented-out logic outline):**

1. Download raw Census tables from `data.gov.in` API
2. Process age distribution into 5-year bins (0–4, 5–9, …, 80+)
3. Process household size distribution (1-person to 10+ person)
4. Derive income proxy by mapping worker categories to PLFS wage brackets:
   - Cultivator → ₹5,000–8,000/month
   - Agricultural Labourer → ₹4,000–6,000/month
   - Household Industry → ₹8,000–15,000/month
   - Other Workers → ₹10,000–50,000/month
   - Non-workers → ₹0

**Planned Outputs:**

- `processed_data/delhi_age_distribution.csv`
- `processed_data/delhi_household_size.csv`
- `processed_data/delhi_income_proxy.csv`

**Status:** Fully designed with detailed docstrings, logic comments, and implementation notes — but all code is commented out.

---

### 2.3 Pipeline 3a: `3_fetch_monsoon_weather.py` ✅ IMPLEMENTED & EXECUTED

**Purpose:** Fetch historical monsoon season weather data from Open-Meteo API.

**Configuration:**

- Location: New Delhi (28.6328, 77.2197)
- Timeframe: 1 June 2025 – 30 September 2025 (monsoon season)
- Source: Open-Meteo Historical Weather API

**Variables Collected:**

- `rain_mm` — Daily rainfall sum
- `max_temp_c` — Daily maximum temperature (2m)
- `max_humidity_pct` — Daily maximum relative humidity (2m)

**Features:**

- Windows console encoding fix (UTF-8)
- Automated **fallback data generation** using random distributions within realistic IMD baselines if the API fails
- Timeout handling (15-second timeout on API requests)

**Output Generated:**

- `processed_data/weather_delhi.csv` — 122 daily weather records (2,993 bytes)

---

### 2.4 Pipeline 3b: `3_generate_population.py` ✅ IMPLEMENTED (Script Ready)

**Purpose:** Generate a synthetic population of agents for the simulation, anchored to the OSM street network.

**Configuration:**

- Number of agents: 5,000
- Source network: `processed_data/network.graphml`

**Agent Attributes Generated:**

| Attribute        | Method                       | Details                                                                 |
| ---------------- | ---------------------------- | ----------------------------------------------------------------------- |
| `id`             | Sequential                   | `agent_00001` to `agent_05000`                                          |
| `home_node`      | Random OSM node              | From loaded network                                                     |
| `work_node`      | Random OSM node              | Guaranteed different from home                                          |
| `income_bracket` | Weighted random (1–5)        | Weights: 20%, 40%, 25%, 10%, 5%                                         |
| `has_car`        | Income-correlated            | Probabilities: 5%→85% by bracket                                        |
| `has_bike`       | Income-correlated            | Probabilities: 50%→10% (inverse)                                        |
| `age`            | Gaussian distribution        | Mean=35, SD=12, clamped 18–70                                           |
| `occupation`     | Weighted random              | Corporate(30%), Service(25%), Student(20%), Labor(15%), Unemployed(10%) |
| `has_metro_pass` | Occupation+income correlated | Higher for Corporate/Student and income ≥ 4                             |

**Planned Output:**

- `processed_data/synthetic_population.parquet`

---

## 3. Processed Data — Generated Outputs

All analysis-ready outputs are stored in `data/processed_data/`.

| File                 | Size    | Format     | Description                                      | Source         |
| -------------------- | ------- | ---------- | ------------------------------------------------ | -------------- |
| `network.graphml`    | 7.67 MB | GraphML    | Full OSM street network for NetworkX             | Pipeline 1     |
| `nodes.parquet`      | 0.31 MB | GeoParquet | 7,064 nodes with coordinates                     | Pipeline 1     |
| `edges.parquet`      | 0.99 MB | GeoParquet | 17,594 edges with road attributes                | Pipeline 1     |
| `weather_delhi.csv`  | 2.9 KB  | CSV        | 122 daily monsoon weather records (Jun–Sep 2025) | Pipeline 3a    |
| `bus_routes.json`    | 1.8 KB  | JSON       | 5 DTC bus routes with stop coordinates           | Manual/curated |
| `metro_network.json` | 1.3 KB  | JSON       | 5 DMRC metro stations + 4 line segments          | Manual/curated |
| `.gitkeep`           | 3 bytes | —          | Directory placeholder for Git                    | —              |

### 3.1 Bus Routes (`bus_routes.json`)

Manually curated JSON file containing **5 DTC bus routes** in the study area:

| Route ID  | Route Name                     | Number of Stops                   |
| --------- | ------------------------------ | --------------------------------- |
| `route_1` | Mudrika Seva (Inner Ring Road) | 4 stops                           |
| `route_2` | Teevra Mudrika                 | 4 stops                           |
| `route_3` | Route 440                      | 4 stops (from Kashmere Gate ISBT) |
| `route_4` | Route 522                      | 4 stops (from Ambedkar Nagar)     |
| `route_5` | Route 85                       | 4 stops (from Anand Vihar ISBT)   |

All routes converge at or near Connaught Place / Rajiv Chowk.

### 3.2 Metro Network (`metro_network.json`)

Manually curated JSON file containing **5 DMRC metro stations** and **4 line segments** near Rajiv Chowk:

**Stations:**

| Station ID        | Name            | Line(s)      | Coordinates      |
| ----------------- | --------------- | ------------ | ---------------- |
| `rajiv_chowk`     | Rajiv Chowk     | Yellow, Blue | 28.6328, 77.2197 |
| `new_delhi`       | New Delhi       | Yellow       | 28.6430, 77.2223 |
| `patel_chowk`     | Patel Chowk     | Yellow       | 28.6231, 77.2144 |
| `barakhamba_road` | Barakhamba Road | Blue         | 28.6293, 77.2268 |
| `rk_ashram_marg`  | RK Ashram Marg  | Blue         | 28.6385, 77.2078 |

**Segments (with travel times):**

- New Delhi → Rajiv Chowk (Yellow, 3 min)
- Rajiv Chowk → Patel Chowk (Yellow, 2 min)
- RK Ashram Marg → Rajiv Chowk (Blue, 3 min)
- Rajiv Chowk → Barakhamba Road (Blue, 2 min)

---

## 4. Validation Data — Reference Datasets

Located in `data/validation_data/`. These are reference datasets for validating simulation outputs.

### 4.1 DMRC Ridership (`dmrc_ridership.csv`)

Daily footfall estimates for metro stations in the study area (2023 data):

| Station         | Daily Footfall | Line        |
| --------------- | -------------- | ----------- |
| Rajiv Chowk     | 500,000        | Yellow/Blue |
| New Delhi       | 400,000        | Yellow      |
| Patel Chowk     | 80,000         | Yellow      |
| Barakhamba Road | 120,000        | Blue        |
| RK Ashram Marg  | 100,000        | Blue        |

### 4.2 Mode Share (`mode_share_delhi.csv`)

Transport mode share for Delhi (2018 source year):

| Mode        | Percentage Share |
| ----------- | ---------------- |
| Two-Wheeler | 28.5%            |
| Walk/Auto   | 26.0%            |
| Bus         | 18.0%            |
| Metro       | 15.5%            |
| Car         | 12.0%            |

---

## 5. Cache — OSMnx HTTP Cache

Located in `data/cache/`. Contains **2 cached API responses** from OSMnx HTTP requests:

| File                 | Size    | Created     |
| -------------------- | ------- | ----------- |
| `1841be17...4e.json` | 1.40 MB | 31 May 2026 |
| `3014484d...ca.json` | 3.84 MB | 6 June 2026 |

These are SHA-1-hashed request/response caches from the Overpass API. They ensure subsequent pipeline runs can use cached data without re-downloading from OSM.

---

## 6. Raw Data

Located in `data/raw_data/`. Currently contains only a `.gitkeep` placeholder.

- Raw data files are intended to be populated by pipeline scripts.
- Files here should be treated as **immutable once downloaded**.
- Currently empty because Pipeline 1 writes directly to `processed_data/` and Pipeline 2 (census) is not yet implemented.

---

## 7. Documentation & Governance

### 7.1 `README.md` (4.9 KB)

Comprehensive project documentation covering:

- Project overview and study area definition
- Full folder structure with descriptions
- Data provenance table (source, license, status per dataset)
- Detailed descriptions of each data source
- Step-by-step "How to Run" instructions
- Dependency table
- Notes on best practices

### 7.2 `CLAUDE.md` (601 bytes)

AI agent guidance document:

- Declares technical scope (ingestion pipelines, data processing, datasets, schemas)
- **Critical rule:** Pushing to `main` branch is strictly prohibited; all work goes to `dev` branch
- Directs agents to read `rule.md` before any git operations

### 7.3 `rule.md` (1.7 KB)

Git branch policy and execution rules:

- **`dev`** is the target branch for all development
- **`main`** is protected (stable release states only)
- Feature branches should be created off `dev`
- Merges to `main` require pull requests with reviews
- Agents must verify branch with `git branch --show-current` before any push
- Policy active since 28 May 2026

### 7.4 `work_summary.md` (1.6 KB)

Previous work summary covering:

- Dependency resolution (osmnx fix)
- Study area radius update (2 km → 4 km)
- Pipeline 1 execution results

---

## 8. Complete File Inventory

```text
data/
├── .gitignore                          (403 B)   — Version control exclusions
├── .gitkeep                            (0 B)     — Directory placeholder
├── CLAUDE.md                           (601 B)   — AI agent guidance
├── README.md                           (4.9 KB)  — Project documentation
├── requirements.txt                    (106 B)   — Python dependencies
├── rule.md                             (1.7 KB)  — Git branch policy
├── work_summary.md                     (1.6 KB)  — Previous work summary
│
├── cache/                                        — OSMnx HTTP cache
│   ├── 1841be17...4e.json              (1.4 MB)  — Cached API response
│   └── 3014484d...ca.json              (3.8 MB)  — Cached API response
│
├── pipelines/                                    — Data acquisition scripts
│   ├── 1_download_osm_network.py       (5.3 KB)  ✅ Implemented & executed
│   ├── 2_fetch_census_demographics.py  (6.4 KB)  ⏳ Placeholder (logic outline)
│   ├── 3_fetch_monsoon_weather.py      (2.0 KB)  ✅ Implemented & executed
│   └── 3_generate_population.py        (3.2 KB)  ✅ Implemented (script ready)
│
├── processed_data/                               — Analysis-ready outputs
│   ├── .gitkeep                        (3 B)
│   ├── network.graphml                 (7.7 MB)  ✅ OSM street network
│   ├── nodes.parquet                   (320 KB)  ✅ 7,064 network nodes
│   ├── edges.parquet                   (1.0 MB)  ✅ 17,594 network edges
│   ├── weather_delhi.csv               (2.9 KB)  ✅ 122 weather records
│   ├── bus_routes.json                 (1.8 KB)  ✅ 5 DTC bus routes
│   └── metro_network.json              (1.3 KB)  ✅ 5 metro stations
│
├── raw_data/                                     — Unmodified source downloads
│   └── .gitkeep                        (3 B)     — (empty, awaiting census data)
│
├── validation_data/                              — Reference data for validation
│   ├── .gitkeep                        (0 B)
│   ├── dmrc_ridership.csv              (213 B)   ✅ 5 stations, daily footfall
│   └── mode_share_delhi.csv            (126 B)   ✅ 5 transport modes
│
└── venv/                                         — Python virtual environment
                                                    (not committed to Git)
```

---

## Summary of Work Status

| Work Item                          | Status          | Details                                  |
| ---------------------------------- | --------------- | ---------------------------------------- |
| Environment setup (venv + deps)    | ✅ Done         | All 7 packages installed                 |
| `.gitignore` configuration         | ✅ Done         | Excludes venv, cache, data files         |
| Git branch policy (`rule.md`)      | ✅ Done         | `dev` branch only                        |
| Study area update (2 km → 4 km)    | ✅ Done         | README + pipeline config                 |
| Pipeline 1: OSM Network            | ✅ Executed     | 7,064 nodes, 17,594 edges                |
| Pipeline 2: Census Demographics    | ⏳ Placeholder  | Logic designed, code commented out       |
| Pipeline 3a: Monsoon Weather       | ✅ Executed     | 122 records, Jun–Sep 2025                |
| Pipeline 3b: Synthetic Population  | ✅ Script ready | 5,000 agents with 9 attributes           |
| Bus routes data                    | ✅ Created      | 5 routes, 20 stops                       |
| Metro network data                 | ✅ Created      | 5 stations, 4 segments                   |
| DMRC ridership validation          | ✅ Created      | 5 stations with footfall estimates       |
| Mode share validation              | ✅ Created      | 5 transport modes                        |
| README documentation               | ✅ Done         | Full project docs                        |
| OSMnx cache                        | ✅ Active       | 2 cached API responses (~5.2 MB)         |

**Total data generated:** ~9.8 MB of processed outputs across 6 files  
**Total files in folder:** 24 files (excluding venv) across 6 subdirectories
