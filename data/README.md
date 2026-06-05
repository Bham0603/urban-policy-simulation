# Data Subsystem

This subsystem is responsible for fetching, processing, and caching the data required for the Urban Policy Simulation.

## Data Provenance

### Road Network
- **Source**: OpenStreetMap (OSM) via `OSMnx`
- **Location**: Rajiv Chowk Metro Station, New Delhi, India `(28.6328, 77.2197)`
- **Radius**: 4,000 meters (4 km)
- **Pipeline**: `pipelines/1_download_osm_network.py`
- **Details**: Extracts the drivable road network, filters to the largest Strongly Connected Component (SCC), and projects to the local UTM zone. Object/mixed columns are string-cast before Parquet serialization.

### Weather Data
- **Source**: Open-Meteo Historical Weather API
- **Location**: New Delhi, India `(Lat: 28.6328, Lon: 77.2197)`
- **Timeframe**: Monsoon season (June 1st to September 30th)
- **Pipeline**: `pipelines/3_fetch_monsoon_weather.py`
- **Details**: Fetches historical daily weather variables (rain sum, max temp, max relative humidity). Includes fallback data generation using realistic IMD baselines if the API call encounters network connectivity issues.
