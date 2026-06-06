"""
Pipeline 1: Download OSM Drivable Street Network — Rajiv Chowk, New Delhi
=========================================================================

Downloads the drivable street network from OpenStreetMap centered on the
Rajiv Chowk metro station (28.6328° N, 77.2197° E) with a 4 km radius
(covering ~3–5 km study area).

The string query "Rajiv Chowk, New Delhi, India" can be ambiguous (it may
refer to the intersection, the metro station, or the broader area), so we
use explicit coordinates with a fixed radius to guarantee reproducibility.

Outputs (written to ../processed_data/):
    - network.graphml   — full graph for NetworkX analysis
    - nodes.parquet     — GeoDataFrame node list for tabular / GIS workflows
    - edges.parquet     — GeoDataFrame edge list for tabular / GIS workflows
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding (cp1252 cannot handle Unicode from OSM data)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

# -- Configuration ----------------------------------------------------------
# Rajiv Chowk Metro Station coordinates (WGS-84)
CENTER_LAT = 28.6328
CENTER_LNG = 77.2197
RADIUS_M = 4000  # 4 km radius (~3-5 km study area)

NETWORK_TYPE = "drive"  # drivable roads only

# Output paths (relative to this script's location)
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "processed_data"

GRAPHML_PATH = OUTPUT_DIR / "network.graphml"
NODES_PARQUET_PATH = OUTPUT_DIR / "nodes.parquet"
EDGES_PARQUET_PATH = OUTPUT_DIR / "edges.parquet"


def download_network(center_point: tuple, dist: int, network_type: str):
    """Download the street network from OSM within a circular buffer."""
    print(f"[1/5] Downloading {network_type} network "
          f"({dist}m around {center_point}) from OSM...")
    G = ox.graph_from_point(
        center_point,
        dist=dist,
        network_type=network_type,
        simplify=True,
    )
    print(f"       Raw graph: {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges")
    return G


def clean_graph(G):
    """Clean the graph: keep largest strongly-connected component."""
    print("[2/5] Cleaning graph (largest strongly-connected component)...")
    largest_scc = max(nx.strongly_connected_components(G), key=len)
    G_clean = G.subgraph(largest_scc).copy()
    print(f"       Cleaned graph: {G_clean.number_of_nodes()} nodes, "
          f"{G_clean.number_of_edges()} edges")
    return G_clean


def project_graph(G):
    """Project the graph to the appropriate UTM zone for metric accuracy."""
    print("[3/5] Projecting graph to UTM...")
    G_proj = ox.project_graph(G)
    return G_proj


def cast_object_cols_to_string(gdf):
    """Coerce columns with mixed types (list / scalar) to strings for Parquet.
    OSM data frequently has list-valued fields (osmid, name, ref, etc.)."""
    for col in gdf.columns:
        if col == "geometry":
            continue  # keep geometry native
        if gdf[col].dtype == object:
            gdf[col] = gdf[col].apply(
                lambda x: str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else None
            )
    return gdf


def save_graphml(G, path: Path):
    """Save the graph in GraphML format for NetworkX interoperability."""
    print(f"[4/5] Saving GraphML -> {path}")
    ox.save_graphml(G, filepath=str(path))
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"       Written {size_mb:.2f} MB")


def save_parquet(G, nodes_path: Path, edges_path: Path):
    """Convert the graph to GeoDataFrame nodes + edges and save as Parquet."""
    print(f"[5/5] Saving Parquet node & edge lists...")

    nodes, edges = ox.graph_to_gdfs(G)

    # Cast object columns to strings for PyArrow compatibility
    nodes = cast_object_cols_to_string(nodes)
    edges = cast_object_cols_to_string(edges)

    nodes.to_parquet(str(nodes_path), engine="pyarrow", index=True)
    edges.to_parquet(str(edges_path), engine="pyarrow", index=True)

    nodes_mb = nodes_path.stat().st_size / (1024 * 1024)
    edges_mb = edges_path.stat().st_size / (1024 * 1024)
    print(f"       Nodes: {nodes_mb:.2f} MB  ({len(nodes)} nodes)")
    print(f"       Edges: {edges_mb:.2f} MB  ({len(edges)} edges)")


def main():
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Download
    G = download_network((CENTER_LAT, CENTER_LNG), RADIUS_M, NETWORK_TYPE)

    # 2. Clean
    G = clean_graph(G)

    # 3. Project to UTM (Skipping so we retain WGS84 lat/lon)
    # G = project_graph(G)

    # 4. Save GraphML
    save_graphml(G, GRAPHML_PATH)

    # 5. Save Parquet node & edge lists
    save_parquet(G, NODES_PARQUET_PATH, EDGES_PARQUET_PATH)

    # Summary
    print("\n[OK] Pipeline complete.")
    print(f"  GraphML       : {GRAPHML_PATH}")
    print(f"  Nodes Parquet : {NODES_PARQUET_PATH}")
    print(f"  Edges Parquet : {EDGES_PARQUET_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[FAIL] Pipeline failed: {exc}", file=sys.stderr)
        sys.exit(1)
