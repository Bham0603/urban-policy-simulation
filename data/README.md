# SUB-04 — Data Engineering

**Urban Intelligence Platform (UIP)**
*Study Area: Rajiv Chowk, New Delhi, India*

---

## Overview

This module handles all data acquisition, cleaning, and transformation pipelines
for the Urban Intelligence Platform. The primary focus area is a **4 km radius
around Rajiv Chowk Metro Station** (28.6328° N, 77.2197° E) in central New Delhi.

## Folder Structure

```text
data/
├── README.md                 ← You are here
├── requirements.txt          ← Python dependencies
├── venv/                     ← Python virtual environment (not committed)
│
├── raw_data/                 ← Unmodified source data downloads
│   └── (populated by pipeline scripts)
│
├── processed_data/           ← Cleaned, analysis-ready outputs
│   ├── network.graphml       ← OSM street network (GraphML)
│   ├── nodes.parquet         ← OSM node list (GeoParquet)
│   ├── edges.parquet         ← OSM edge list (GeoParquet)
│   ├── weather_delhi.csv     ← Historical monsoon weather data
│   ├── delhi_age_distribution.csv     ← Census 2011 age cohorts
│   ├── delhi_household_size.csv       ← Census 2011 household sizes
│   ├── delhi_income_proxy.csv         ← Census 2011 × PLFS income proxy
│   └── synthetic_population.parquet   ← 5,000 synthetic agents
│
├── validation_data/          ← Data for validation purposes
│
├── cache/                    ← OSMnx HTTP cache
│
└── pipelines/                ← Data acquisition & processing scripts
    ├── 1_download_osm_network.py
    ├── 2_fetch_census_demographics.py
    ├── 3_generate_population.py
    └── 3_fetch_monsoon_weather.py
```

## Data Provenance

| Dataset | Source | License | Status |
| ------- | ------ | ------- | ------ |
| Street Network | [OpenStreetMap](https://www.openstreetmap.org/) via `osmnx` | ODbL 1.0 | ✅ Implemented |
| Monsoon Weather | [Open-Meteo Historical API](https://open-meteo.com/) | CC BY 4.0 | ✅ Implemented |
| Census Demographics | [Census of India 2011](https://censusindia.gov.in/) (Tables C-13, HH-1, B-4) | Government Open Data | ✅ Implemented |
| Synthetic Population | Derived from Census 2011 distributions + OSM network | — | ✅ Implemented |

### OpenStreetMap Network

- **Query**: Point-based, 4 km radius around (28.6328, 77.2197) covering ~3–5 km study area
- **Network type**: `drive` (drivable roads only)
- **Cleaning**: Largest strongly-connected component retained
- **Projection**: Projected to local UTM zone for metric measurement accuracy
- **Formats**: GraphML (for NetworkX), Parquet node + edge lists (for pandas/geopandas)
- **Mixed-type handling**: Object/mixed columns are explicitly string-cast before Parquet serialization to prevent PyArrow data-type mismatch errors

### Monsoon Weather Data

- **Source**: Open-Meteo Historical Weather API
- **Location**: New Delhi, India (Lat: 28.6328, Lon: 77.2197)
- **Timeframe**: Monsoon season (June 1st to September 30th)
- **Variables**: `rain_mm`, `max_temp_c`, `max_humidity_pct`
- **Fallback**: Includes automated fallback data generation using realistic IMD historical baselines if the API call encounters network connectivity issues

### Census Demographics

- **Source**: Census of India 2011 — [censusindia.gov.in](https://censusindia.gov.in/)
- **Tables used**:
  - **C-13** — Single Year Age Returns by Residence and Sex → 5-year age cohorts for NCT of Delhi
  - **HH-1** — Households by Size → household size distribution (mean ≈ 4.5 members)
  - **B-4** — Main Workers by Industrial Category → income proxy via cross-reference with PLFS 2019-20 wage brackets
- **Income proxy**: Worker categories (Cultivator, Agri Labourer, HH Industry, Other Workers, Non-workers) mapped to standard PLFS (Periodic Labour Force Survey) 2019-20 income brackets in INR/month
- **Geographic filter**: NCT of Delhi (urban)
- **Fallback**: If the data.gov.in API is unavailable, a deterministic synthetic baseline is generated using published Census 2011 summary statistics with fixed random seed (42) for reproducibility
- **Outputs**: `delhi_age_distribution.csv`, `delhi_household_size.csv`, `delhi_income_proxy.csv`

### DMRC Ridership

- **Source**: DMRC (Delhi Metro Rail Corporation) 2023 Annual Report
- **Key metric**: Rajiv Chowk station ≈ 500,000 daily footfall (highest ridership station on the network)
- **Usage**: Calibration anchor for metro demand in the synthetic population model

### Mode Share

- **Source**: Delhi 2018 State Transport Survey (Government of NCT of Delhi, Transport Department)
- **Key metrics**:
  - Metro: **15.5%** of total motorised trips
  - Bus (DTC + cluster): **18.0%** of total motorised trips
- **Usage**: Baseline modal split for validating agent mode-choice distributions

### Synthetic Population

- **Agents**: 5,000 synthetic agents within the 4 km study area
- **Demographics**: Age, household size, and income bracket sampled via weighted random draws from Census 2011 distributions (see above)
- **Spatial**: Home and work nodes drawn from the OSM street network (7,064 nodes)
- **Behavioral**: Vehicle ownership (car, bike) and metro pass correlated with income tier and occupation
- **Idempotency**: Fixed random seed (42) ensures identical output on every run
- **Output**: `synthetic_population.parquet` (5,000 rows, 12 columns, zero nulls)

## How to Run

### 1. Environment Setup

```bash
# Navigate to this directory
cd data

# Create and activate the virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the OSM Network Pipeline

```bash
python pipelines/1_download_osm_network.py
```

**Expected output:**

- `processed_data/network.graphml` — Full graph in GraphML format
- `processed_data/nodes.parquet` — Node list as GeoParquet
- `processed_data/edges.parquet` — Edge list as GeoParquet

### 3. Run the Monsoon Weather Pipeline

```bash
python pipelines/3_fetch_monsoon_weather.py
```

**Expected output:**

- `processed_data/weather_delhi.csv` — 122 daily weather records

### 4. Run the Census Demographics Pipeline

```bash
python pipelines/2_fetch_census_demographics.py
```

**Expected output:**

- `processed_data/delhi_age_distribution.csv` — 17 age cohorts (5-year bins)
- `processed_data/delhi_household_size.csv` — 10 household size categories
- `processed_data/delhi_income_proxy.csv` — 5 income brackets (INR/month)

### 5. Run the Synthetic Population Pipeline

```bash
python pipelines/3_generate_population.py
```

**Expected output:**

- `processed_data/synthetic_population.parquet` — 5,000 agents with demographics

## Dependencies

| Package | Purpose |
| ------- | ------- |
| `osmnx>=2.1.0` | OpenStreetMap network download & analysis |
| `geopandas>=1.0.0` | Geospatial DataFrames & Parquet export |
| `pandas>=2.2.0` | Tabular data processing |
| `shapely>=2.0.0` | Geometric operations |
| `networkx>=3.3` | Graph data structures (bundled with osmnx) |
| `pyarrow>=15.0.0` | Parquet file I/O engine |
| `requests>=2.31.0` | HTTP requests for weather API |

## Notes

- The virtual environment (`venv/`) should **not** be committed to version control.
- Raw data files in `raw_data/` should be treated as immutable once downloaded.
- All processed outputs are reproducible by re-running the pipeline scripts.
- UTF-8 encoding is enforced on Windows to prevent console charmap encoding crashes.
