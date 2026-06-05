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
│   └── weather_delhi.csv     ← Historical monsoon weather data
│
├── validation_data/          ← Data for validation purposes
│
├── cache/                    ← OSMnx HTTP cache
│
└── pipelines/                ← Data acquisition & processing scripts
    ├── 1_download_osm_network.py
    ├── 2_fetch_census_demographics.py  (placeholder)
    └── 3_fetch_monsoon_weather.py
```

## Data Provenance

| Dataset | Source | License | Status |
| ------- | ------ | ------- | ------ |
| Street Network | [OpenStreetMap](https://www.openstreetmap.org/) via `osmnx` | ODbL 1.0 | ✅ Implemented |
| Monsoon Weather | [Open-Meteo Historical API](https://open-meteo.com/) | CC BY 4.0 | ✅ Implemented |
| Census Demographics | [Census of India 2011](https://censusindia.gov.in/) | Government Open Data | ⏳ Placeholder |

### OpenStreetMap Network

- **Query**: Point-based, 4 km radius around (28.6328, 77.2197)
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

### Census Demographics (Planned)

- **Tables**: C-13 (age), HH-1/HH-2 (household size), B-4 (worker categories)
- **Income proxy**: Worker categories mapped to PLFS wage brackets
- **Geographic filter**: NCT of Delhi

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

### 4. Census Demographics (Not Yet Implemented)

```bash
# python pipelines/2_fetch_census_demographics.py
# See the script for detailed implementation notes
```

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
