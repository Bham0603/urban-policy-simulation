# Data Folder Work Summary

This document summarizes the recent changes and pipeline executions within the `data` directory of the Urban Intelligence Platform.

## 1. Dependency Resolution

- Identified missing Python module errors (specifically `osmnx`).
- Successfully installed all project dependencies using `pip install -r requirements.txt`. This installed `osmnx`, `geopandas`, `pandas`, `shapely`, `networkx`, and other necessary packages into the environment.

## 2. Configuration & Documentation Updates

- Updated the `README.md` to formally adjust the study area around Rajiv Chowk Metro Station from a 2 km radius to a **4 km radius** (covering a ~3–5 km study area).
- Validated that the `1_download_osm_network.py` script was correctly configured to use `RADIUS_M = 4000`.

## 3. OSM Network Pipeline Execution

- Executed Pipeline 1: `1_download_osm_network.py`.
- Downloaded the drivable street network from OpenStreetMap centered on Rajiv Chowk (28.6328° N, 77.2197° E) with the configured 4 km radius.
- **Processing Steps Completed:**
  - Fetched raw graph (7,236 nodes, 17,985 edges).
  - Cleaned the graph by retaining only the largest strongly-connected component.
  - Projected the graph to the local UTM zone for accurate metric measurements.
  - Exported outputs to the `processed_data` directory.
- **Generated Artifacts:**
  - `processed_data/network.graphml` (7.67 MB) - Full graph for NetworkX interoperability.
  - `processed_data/nodes.parquet` (0.31 MB) - 7,064 nodes formatted for tabular/GIS workflows.
  - `processed_data/edges.parquet` (0.99 MB) - 17,594 edges formatted for tabular/GIS workflows.
