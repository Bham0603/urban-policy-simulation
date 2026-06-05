import sys
import os
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd

# Enforce strict UTF-8 handling for console logs
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

print("Starting OSM pipeline...")

# Coordinate for Rajiv Chowk, New Delhi
lat, lon = 28.6328, 77.2197
dist = 4000

# 1. Download the network
print(f"Downloading drivable road network within {dist}m of ({lat}, {lon})...")
G = ox.graph_from_point((lat, lon), dist=dist, network_type='drive')

# 2. Filter to largest strongly connected component
print("Filtering to the largest strongly connected component...")
largest_scc = max(nx.strongly_connected_components(G), key=len)
G = G.subgraph(largest_scc).copy()

# 3. Project to appropriate UTM zone
print("Projecting graph...")
G_proj = ox.project_graph(G)

# Ensure processed_data directory exists
os.makedirs('processed_data', exist_ok=True)

# 4. Export graphml
print("Exporting network to GraphML...")
ox.save_graphml(G_proj, filepath='processed_data/network.graphml')

# 5. Extract nodes and edges and save to GeoParquet
print("Extracting nodes and edges...")
nodes, edges = ox.graph_to_gdfs(G_proj)

def cast_object_cols_to_string(gdf):
    for col in gdf.columns:
        if gdf[col].dtype == 'object':
            gdf[col] = gdf[col].apply(lambda x: str(x) if x is not None and not (isinstance(x, float) and pd.isna(x)) else None)
    return gdf

print("Casting object/mixed columns to strings...")
nodes = cast_object_cols_to_string(nodes)
edges = cast_object_cols_to_string(edges)

print("Exporting nodes to GeoParquet...")
nodes.to_parquet('processed_data/nodes.parquet')

print("Exporting edges to GeoParquet...")
edges.to_parquet('processed_data/edges.parquet')

print("Pipeline 1 complete.")
print(f"Nodes exported: {len(nodes)}")
print(f"Edges exported: {len(edges)}")
