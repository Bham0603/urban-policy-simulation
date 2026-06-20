"""Transportation & multi-modal network graph.

Represents roads, buses, and metro lines with routing and congestion capabilities.

Supports two construction modes:
  1. Synthetic grid (default __init__) — 10×10 intersection grid for dev/testing
  2. Real OSM data (load_from_osm classmethod) — loads GraphML + metro/bus JSON
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import TypedDict

import networkx as nx

# Central coordinates — Rajiv Chowk Metro Station, New Delhi
# Study area: ~3–5 km radius around this point
CITY_LAT = 28.6328
CITY_LON = 77.2197

# Default travel speed constants (meters per second)
WALK_SPEED = 1.4  # ~5 km/h
BIKE_SPEED = 4.2  # ~15 km/h
BIKE_SHARE_SPEED = 3.8  # ~14 km/h (slightly slower due to heavier docked bikes)
BUS_BASE_SPEED = 6.0  # ~22 km/h
METRO_SPEED = 12.0  # ~43 km/h
CAR_FREE_FLOW_SPEED = 11.0  # ~40 km/h
E_RICKSHAW_SPEED = 3.3  # ~12 km/h

# Highway classification → (capacity vehicles/tick, free_flow_speed m/s)
# Capacity reflects PCU (Passenger Car Units) per lane per hour, scaled to
# simulation tick granularity.  Values calibrated for Indian mixed-traffic.
_HIGHWAY_CAPACITY: dict[str, tuple[float, float]] = {
    "motorway": (2000.0, 22.0),  # ~80 km/h
    "motorway_link": (1500.0, 16.0),  # ~58 km/h
    "trunk": (1500.0, 16.0),  # ~58 km/h
    "trunk_link": (1200.0, 14.0),  # ~50 km/h
    "primary": (1200.0, 14.0),  # ~50 km/h
    "primary_link": (1000.0, 12.0),  # ~43 km/h
    "secondary": (800.0, 11.0),  # ~40 km/h
    "secondary_link": (600.0, 10.0),  # ~36 km/h
    "tertiary": (600.0, 10.0),  # ~36 km/h
    "tertiary_link": (500.0, 9.0),  # ~32 km/h
    "residential": (300.0, 8.0),  # ~29 km/h
    "living_street": (200.0, 5.5),  # ~20 km/h
    "unclassified": (400.0, 8.0),  # ~29 km/h
    "busway": (500.0, 9.0),  # ~32 km/h
}
_DEFAULT_CAPACITY = (300.0, CAR_FREE_FLOW_SPEED)


class SegmentInfo(TypedDict):
    length: float
    capacity: float
    free_flow_speed: float
    flow: int
    metro_line: str | None
    bus_route: str | None


class MultiModalNetwork:
    """Multi-modal transportation network (Roads, Metro, Bus).

    Maintains a physical NetworkX graph of roads and transit routes,
    updating dynamic travel times using a BPR congestion model.
    """

    def __init__(self, size: int = 10, spacing: float = 0.005) -> None:
        """Initialize the synthetic multi-modal Delhi (Rajiv Chowk) grid.

        size: grid size (e.g. 10x10 intersections covering ~5 km)
        spacing: coordinate distance between adjacent grid intersections (~555 m)
        """
        self.g = nx.DiGraph()
        self.size = size
        self.spacing = spacing
        self._is_real_data = False

        # High-performance routing cache: (source, target, mode) -> path
        self._routing_cache: dict[tuple[str, str, str], list[str] | None] = {}

        # Track active policies & dynamic settings internally
        self._disabled_metro_lines: set[str] = set()
        self._bus_capacity_multiplier: float = 1.0
        self._fuel_price_delta_paise: int = 0
        self._weather_rain_intensity: float = 0.0

        # Bounding box (computed dynamically for real data)
        self._lat_min: float = CITY_LAT - (size / 2) * spacing
        self._lat_max: float = CITY_LAT + (size / 2) * spacing
        self._lon_min: float = CITY_LON - (size / 2) * spacing
        self._lon_max: float = CITY_LON + (size / 2) * spacing

        # Build synthetic road intersections (Grid nodes)
        self._build_road_nodes()
        self._build_road_links()

        # Build Transit lines (Delhi Metro Yellow and Blue lines, major bus routes)
        self._build_metro_system()
        self._build_bus_system()

    # ------------------------------------------------------------------
    # Class method: construct from real OSM data
    # ------------------------------------------------------------------

    @classmethod
    def load_from_osm(
        cls,
        graphml_path: str | Path,
        metro_json_path: str | Path | None = None,
        bus_json_path: str | Path | None = None,
    ) -> "MultiModalNetwork":
        """Construct a MultiModalNetwork from real OSM data files.

        Parameters:
            graphml_path:   Path to the OSM road network GraphML file
            metro_json_path: Path to metro_network.json (optional)
            bus_json_path:   Path to bus_routes.json (optional)

        Returns:
            A fully wired MultiModalNetwork backed by real road geometry.
        """
        import osmnx as ox

        graphml_path = Path(graphml_path)
        if not graphml_path.exists():
            raise FileNotFoundError(f"GraphML not found: {graphml_path}")

        # Load the OSM graph (MultiDiGraph)
        osm_graph = ox.load_graphml(graphml_path)

        # Create instance via __new__ to skip synthetic __init__
        net = cls.__new__(cls)
        net.g = nx.DiGraph()
        net.size = 0
        net.spacing = 0.0
        net._is_real_data = True
        net._routing_cache = {}
        net._disabled_metro_lines = set()
        net._bus_capacity_multiplier = 1.0
        net._fuel_price_delta_paise = 0
        net._weather_rain_intensity = 0.0

        # --- Convert OSM MultiDiGraph → our internal DiGraph ---
        net._load_osm_road_graph(osm_graph)

        # --- Compute bounding box from real node coordinates ---
        lats = [d["lat"] for _, d in net.g.nodes(data=True) if "lat" in d]
        lons = [d["lon"] for _, d in net.g.nodes(data=True) if "lon" in d]
        if lats and lons:
            net._lat_min = min(lats)
            net._lat_max = max(lats)
            net._lon_min = min(lons)
            net._lon_max = max(lons)
        else:
            net._lat_min = CITY_LAT - 0.04
            net._lat_max = CITY_LAT + 0.04
            net._lon_min = CITY_LON - 0.04
            net._lon_max = CITY_LON + 0.04

        # --- Overlay transit if data files provided ---
        if metro_json_path:
            net._load_metro_from_json(Path(metro_json_path))

        if bus_json_path:
            net._load_bus_from_json(Path(bus_json_path))

        return net

    def _load_osm_road_graph(self, osm_graph: nx.MultiDiGraph) -> None:
        """Convert an OSMnx MultiDiGraph into our internal DiGraph.

        - Node IDs become strings (str(osmid)) for consistency
        - Each node gets type="intersection", lat, lon
        - Each edge gets type="road" with capacity inferred from highway tag
        - For multi-edges, we keep only the shortest one per (u, v) pair
        """
        # Add nodes
        for node_id, data in osm_graph.nodes(data=True):
            str_id = str(node_id)
            lat = float(data.get("y", 0.0))
            lon = float(data.get("x", 0.0))
            self.g.add_node(
                str_id,
                type="intersection",
                lat=lat,
                lon=lon,
                street_count=int(data.get("street_count", 0)),
            )

        # Add edges — for MultiDiGraph, keep shortest edge per (u, v) pair
        best_edges: dict[tuple[str, str], dict] = {}

        for u, v, key, data in osm_graph.edges(data=True, keys=True):
            str_u = str(u)
            str_v = str(v)
            pair = (str_u, str_v)

            length = float(data.get("length", 100.0))

            # Only keep shortest edge for each (u, v) pair
            if pair in best_edges and best_edges[pair]["length"] <= length:
                continue

            # Infer capacity from highway classification
            highway = data.get("highway", "residential")
            if isinstance(highway, list):
                highway = highway[0] if highway else "residential"
            highway = str(highway)

            # Strip list notation if serialised as string
            if highway.startswith("["):
                highway = highway.strip("[]' ").split("'")[0].strip(", '")

            capacity, free_flow_speed = _HIGHWAY_CAPACITY.get(
                highway, _DEFAULT_CAPACITY
            )

            best_edges[pair] = {
                "type": "road",
                "length": length,
                "capacity": capacity,
                "flow": 0,
                "free_flow_speed": free_flow_speed,
                "metro_line": None,
                "bus_route": None,
                "highway": highway,
            }

        # Add the winning edges
        for (str_u, str_v), attrs in best_edges.items():
            self.g.add_edge(str_u, str_v, **attrs)

    def _load_metro_from_json(self, json_path: Path) -> None:
        """Load metro lines from a JSON file and overlay onto the road graph.

        For each metro line:
        1. Create a metro station node for each station
        2. Snap station to the nearest road intersection node
        3. Add transfer (walking) edges between station and road node
        4. Wire metro track edges between consecutive stations
        """
        with open(json_path, "r", encoding="utf-8") as f:
            metro_data = json.load(f)

        for line_info in metro_data.get("lines", []):
            line_name = line_info["name"].lower().replace(" line", "").strip()
            stations = line_info.get("stations", [])
            segments = line_info.get("segments", [])

            # Build station name → info mapping for segment lookup
            station_map: dict[str, dict] = {}
            station_node_ids: list[str] = []

            for station in stations:
                st_name = station["name"]
                st_lat = float(station["lat"])
                st_lon = float(station["lon"])

                station_id = f"metro_{line_name}_{st_name.lower().replace(' ', '_')}"
                station_map[st_name] = {
                    "id": station_id,
                    "lat": st_lat,
                    "lon": st_lon,
                }
                station_node_ids.append(station_id)

                # Add metro station node
                self.g.add_node(
                    station_id,
                    type="metro_station",
                    line=line_name,
                    lat=st_lat,
                    lon=st_lon,
                )

                # Snap to nearest road node and add transfer edges
                nearest = self.get_nearest_node(st_lat, st_lon)
                if nearest:
                    self.g.nodes[nearest]["metro_station"] = True

                    # Bidirectional transfer (walking to/from platform)
                    for src, dst in [(nearest, station_id), (station_id, nearest)]:
                        self.g.add_edge(
                            src,
                            dst,
                            type="transfer",
                            length=80.0,  # ~80m walk to platform
                            capacity=1e9,
                            flow=0,
                            free_flow_speed=WALK_SPEED,
                            metro_line=None,
                            bus_route=None,
                        )

            # Wire metro tracks using segment data
            for seg in segments:
                from_name = seg["from"]
                to_name = seg["to"]

                if from_name not in station_map or to_name not in station_map:
                    continue

                from_info = station_map[from_name]
                to_info = station_map[to_name]
                from_id = from_info["id"]
                to_id = to_info["id"]

                distance_m = float(seg.get("distance_km", 1.0)) * 1000.0

                # Bidirectional metro tracks
                for src, dst in [(from_id, to_id), (to_id, from_id)]:
                    self.g.add_edge(
                        src,
                        dst,
                        type="metro",
                        line=line_name,
                        length=distance_m,
                        capacity=10000.0,
                        flow=0,
                        free_flow_speed=METRO_SPEED,
                        metro_line=line_name,
                        bus_route=None,
                    )

    def _load_bus_from_json(self, json_path: Path) -> None:
        """Load bus routes from a JSON file and tag road edges.

        For each route:
        1. Snap each bus stop to the nearest road intersection
        2. Tag road edges along the shortest path between consecutive stops
           with the bus route ID
        """
        with open(json_path, "r", encoding="utf-8") as f:
            bus_data = json.load(f)

        for route_info in bus_data.get("routes", []):
            route_id = route_info["id"]
            stops = route_info.get("stops", [])

            snapped_nodes: list[str] = []
            for stop in stops:
                nearest = self.get_nearest_node(float(stop["lat"]), float(stop["lon"]))
                if nearest:
                    self.g.nodes[nearest]["bus_stop"] = True
                    snapped_nodes.append(nearest)

            # Tag edges along the path between consecutive stops
            for i in range(len(snapped_nodes) - 1):
                n1, n2 = snapped_nodes[i], snapped_nodes[i + 1]
                if n1 == n2:
                    continue

                try:
                    path = nx.shortest_path(self.g, n1, n2, weight="length")
                    for j in range(len(path) - 1):
                        u, v = path[j], path[j + 1]
                        if self.g.has_edge(u, v):
                            edge = self.g.edges[u, v]
                            if edge.get("type") == "road":
                                edge["bus_route"] = route_id
                        # Tag reverse direction too
                        if self.g.has_edge(v, u):
                            edge_rev = self.g.edges[v, u]
                            if edge_rev.get("type") == "road":
                                edge_rev["bus_route"] = route_id
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    continue

    # ------------------------------------------------------------------
    # Bounding box accessors (used by engine for grid generation)
    # ------------------------------------------------------------------

    @property
    def lat_min(self) -> float:
        return self._lat_min

    @property
    def lat_max(self) -> float:
        return self._lat_max

    @property
    def lon_min(self) -> float:
        return self._lon_min

    @property
    def lon_max(self) -> float:
        return self._lon_max

    # ------------------------------------------------------------------
    # Cache & property management (unchanged)
    # ------------------------------------------------------------------

    def clear_routing_cache(self) -> None:
        """Clear the routing cache when network conditions or parameters change."""
        self._routing_cache.clear()

    @property
    def disabled_metro_lines(self) -> set[str]:
        return self._disabled_metro_lines

    @disabled_metro_lines.setter
    def disabled_metro_lines(self, value: set[str]) -> None:
        self._disabled_metro_lines = value
        self.clear_routing_cache()

    @property
    def bus_capacity_multiplier(self) -> float:
        return self._bus_capacity_multiplier

    @bus_capacity_multiplier.setter
    def bus_capacity_multiplier(self, value: float) -> None:
        if self._bus_capacity_multiplier != value:
            self._bus_capacity_multiplier = value
            self.clear_routing_cache()

    @property
    def fuel_price_delta_paise(self) -> int:
        return self._fuel_price_delta_paise

    @fuel_price_delta_paise.setter
    def fuel_price_delta_paise(self, value: int) -> None:
        if self._fuel_price_delta_paise != value:
            self._fuel_price_delta_paise = value
            self.clear_routing_cache()

    @property
    def weather_rain_intensity(self) -> float:
        return self._weather_rain_intensity

    @weather_rain_intensity.setter
    def weather_rain_intensity(self, value: float) -> None:
        if self._weather_rain_intensity != value:
            self._weather_rain_intensity = value
            self.clear_routing_cache()

    # ------------------------------------------------------------------
    # Synthetic grid builders (kept as fallback)
    # ------------------------------------------------------------------

    def _build_road_nodes(self) -> None:
        """Create road intersection nodes centered on the city."""
        lat_start = CITY_LAT - (self.size / 2) * self.spacing
        lon_start = CITY_LON - (self.size / 2) * self.spacing

        for r in range(self.size):
            for c in range(self.size):
                node_id = f"node_{r}_{c}"
                lat = lat_start + r * self.spacing
                lon = lon_start + c * self.spacing
                self.g.add_node(
                    node_id, type="intersection", lat=lat, lon=lon, r=r, c=c
                )

    def _build_road_links(self) -> None:
        """Connect intersections with directed grid links (roads)."""
        for r in range(self.size):
            for c in range(self.size):
                curr = f"node_{r}_{c}"

                # Connect horizontally and vertically
                neighbors = []
                if r > 0:
                    neighbors.append(f"node_{r-1}_{c}")
                if r < self.size - 1:
                    neighbors.append(f"node_{r+1}_{c}")
                if c > 0:
                    neighbors.append(f"node_{r}_{c-1}")
                if c < self.size - 1:
                    neighbors.append(f"node_{r}_{c+1}")

                for nbr in neighbors:
                    # Physical distance in meters (approx. 111,000 meters per degree)
                    dx = (
                        (self.g.nodes[nbr]["lon"] - self.g.nodes[curr]["lon"])
                        * 111000
                        * math.cos(math.radians(CITY_LAT))
                    )
                    dy = (self.g.nodes[nbr]["lat"] - self.g.nodes[curr]["lat"]) * 111000
                    length = math.sqrt(dx * dx + dy * dy)

                    # Lanes capacity: segments closer to center have higher capacity
                    dist_to_center = math.sqrt(
                        (r - self.size / 2) ** 2 + (c - self.size / 2) ** 2
                    )
                    capacity = max(100.0, 500.0 - 40.0 * dist_to_center)

                    self.g.add_edge(
                        curr,
                        nbr,
                        type="road",
                        length=length,
                        capacity=capacity,
                        flow=0,
                        free_flow_speed=CAR_FREE_FLOW_SPEED,
                        metro_line=None,
                        bus_route=None,
                    )

    def _build_metro_system(self) -> None:
        """Create Delhi Metro Yellow and Blue lines cutting through the grid.

        Yellow Line runs north-south through Rajiv Chowk (vertical cut).
        Blue Line runs east-west through Rajiv Chowk (horizontal cut).
        Both lines intersect at Rajiv Chowk station (center of grid).
        """
        # Yellow Line: Vertical (north-south) cut through the center column
        yellow_c = self.size // 2
        yellow_nodes = [f"node_{r}_{yellow_c}" for r in range(self.size)]
        self._wire_metro_line("yellow", yellow_nodes)

        # Blue Line: Horizontal (east-west) cut across the center row
        blue_r = self.size // 2
        blue_nodes = [f"node_{blue_r}_{c}" for c in range(self.size)]
        self._wire_metro_line("blue", blue_nodes)

    def _wire_metro_line(self, line_name: str, nodes: list[str]) -> None:
        """Create dedicated metro station nodes, walk-to-transit transfer links, and metro tracks."""
        station_ids = []
        for n in nodes:
            lat = self.g.nodes[n]["lat"]
            lon = self.g.nodes[n]["lon"]
            station_id = f"metro_{line_name}_station_{n}"
            station_ids.append(station_id)

            # Add dedicated metro station node
            self.g.add_node(
                station_id, type="metro_station", line=line_name, lat=lat, lon=lon
            )
            # Mark the physical road intersection as having transit access
            self.g.nodes[n]["metro_station"] = True

            # Add bidirectional transfer edges (50-meter walking link to/from platforms)
            self.g.add_edge(
                n,
                station_id,
                type="transfer",
                length=50.0,
                capacity=1e9,
                flow=0,
                free_flow_speed=WALK_SPEED,
                metro_line=None,
                bus_route=None,
            )
            self.g.add_edge(
                station_id,
                n,
                type="transfer",
                length=50.0,
                capacity=1e9,
                flow=0,
                free_flow_speed=WALK_SPEED,
                metro_line=None,
                bus_route=None,
            )

        # Wire metro tracks between consecutive stations
        for i in range(len(station_ids) - 1):
            s1, s2 = station_ids[i], station_ids[i + 1]

            # Add bidirectional metro links (completely separate from road links)
            for src, dst in [(s1, s2), (s2, s1)]:
                # Physical length matching road segment
                dx = (
                    (self.g.nodes[dst]["lon"] - self.g.nodes[src]["lon"])
                    * 111000
                    * math.cos(math.radians(CITY_LAT))
                )
                dy = (self.g.nodes[dst]["lat"] - self.g.nodes[src]["lat"]) * 111000
                length = math.sqrt(dx * dx + dy * dy)

                self.g.add_edge(
                    src,
                    dst,
                    type="metro",
                    line=line_name,
                    length=length,
                    capacity=10000.0,  # massive capacity
                    flow=0,
                    free_flow_speed=METRO_SPEED,
                    metro_line=line_name,
                    bus_route=None,
                )

    def _build_bus_system(self) -> None:
        """Build major DTC bus routes in the Connaught Place / Rajiv Chowk area."""
        # Outer ring bus loop — represents routes circling the CP outer circle
        # Dynamically compute indices based on grid size
        inner = max(1, self.size // 4)
        outer = min(self.size - 2, self.size - 1 - inner)

        # Build a rectangular loop
        bus_nodes = []
        # Top edge (left to right)
        for c in range(inner, outer + 1):
            bus_nodes.append(f"node_{inner}_{c}")
        # Right edge (top to bottom)
        for r in range(inner + 1, outer + 1):
            bus_nodes.append(f"node_{r}_{outer}")
        # Bottom edge (right to left)
        for c in range(outer - 1, inner - 1, -1):
            bus_nodes.append(f"node_{outer}_{c}")
        # Left edge (bottom to top, closing the loop)
        for r in range(outer - 1, inner, -1):
            bus_nodes.append(f"node_{r}_{inner}")
        # Close the loop
        bus_nodes.append(f"node_{inner}_{inner}")

        for i in range(len(bus_nodes) - 1):
            n1, n2 = bus_nodes[i], bus_nodes[i + 1]
            self.g.nodes[n1]["bus_stop"] = True
            self.g.nodes[n2]["bus_stop"] = True

            # Tag existing road edges with bus route
            for src, dst in [(n1, n2), (n2, n1)]:
                if self.g.has_edge(src, dst):
                    self.g.edges[src, dst]["bus_route"] = "cp_outer_ring"

    # ------------------------------------------------------------------
    # Node lookup
    # ------------------------------------------------------------------

    def get_nearest_node(self, lat: float, lon: float) -> str:
        """Find the nearest road intersection node to a given lat/lon."""
        best_node = None
        min_dist = float("inf")

        for node_id, data in self.g.nodes(data=True):
            if data.get("type") == "intersection":
                d_lat = data["lat"] - lat
                d_lon = data["lon"] - lon
                dist = d_lat * d_lat + d_lon * d_lon
                if dist < min_dist:
                    min_dist = dist
                    best_node = node_id

        if best_node is not None:
            return best_node

        # Absolute fallback — return first intersection node
        for node_id, data in self.g.nodes(data=True):
            if data.get("type") == "intersection":
                return node_id

        return "node_0_0"

    def get_intersection_nodes(self) -> list[str]:
        """Return a list of all road intersection node IDs."""
        return [
            node_id
            for node_id, data in self.g.nodes(data=True)
            if data.get("type") == "intersection"
        ]

    # ------------------------------------------------------------------
    # BPR congestion model (unchanged)
    # ------------------------------------------------------------------

    def compute_bpr_travel_time(self, u: str, v: str, edge_data: dict) -> float:
        """Compute travel time (seconds) on an edge using BPR congestion formula."""
        length = edge_data["length"]
        free_flow_speed = edge_data["free_flow_speed"]
        edge_type = edge_data["type"]

        # Base travel time in seconds
        t_zero = length / free_flow_speed

        if edge_type == "road":
            # Apply weather speed reduction
            # Rain drops car speed by up to 40%
            weather_mult = 1.0 - 0.40 * self.weather_rain_intensity
            speed = free_flow_speed * weather_mult
            t_zero = length / max(1.0, speed)

            # Bureau of Public Roads (BPR) formula
            flow = edge_data["flow"]
            capacity = edge_data["capacity"]
            # Weather reduces lane capacity too by up to 30%
            cap = capacity * (1.0 - 0.30 * self.weather_rain_intensity)

            # Calibrated mixed-traffic BPR formula for Indian roads
            # Mixed-traffic has lower threshold of speed degradation but standard exponential growth
            # We use alpha = 0.20 and beta = 4.0 to make it slightly more sensitive to early traffic (mixed-traffic friction)
            alpha = 0.20
            beta = 4.0
            congestion_term = alpha * ((flow / max(10.0, cap)) ** beta)
            # Cap congestion multiplier to 9.0 to prevent infinite delay spikes
            congestion_term = min(9.0, congestion_term)
            return t_zero * (1.0 + congestion_term)

        elif edge_type == "metro":
            line = edge_data["line"]
            if line in self.disabled_metro_lines:
                return 1e9  # impassable!
            return t_zero

        elif edge_type == "transfer":
            return length / WALK_SPEED

        elif edge_type == "bus":
            return t_zero

        return t_zero

    # ------------------------------------------------------------------
    # Routing (unchanged)
    # ------------------------------------------------------------------

    def find_shortest_path(
        self, source: str, target: str, mode: str
    ) -> list[str] | None:
        """Find the shortest path for a given mode of transport using the routing cache.

        Returns a list of node IDs or None.
        """
        if source == target:
            return [source]

        # Check in high-performance cache
        cache_key = (source, target, mode)
        if cache_key in self._routing_cache:
            return self._routing_cache[cache_key]

        # Define edge weight mapping based on the travel mode
        def weight_func(u: str, v: str, edge_attr: dict) -> float:
            etype = edge_attr["type"]

            if mode == "walk":
                # Walking uses road network only at walk speed
                if etype != "road":
                    return 1e9
                return edge_attr["length"] / WALK_SPEED

            elif mode == "bike":
                # Biking uses road network only at bike speed, with minor rain penalty
                if etype != "road":
                    return 1e9
                rain_penalty = 1.0 + 0.5 * self.weather_rain_intensity
                return (edge_attr["length"] / BIKE_SPEED) * rain_penalty

            elif mode in ("car", "auto"):
                # Cars and autos use road networks and are subject to congestion
                if etype != "road":
                    return 1e9
                return self.compute_bpr_travel_time(u, v, edge_attr)

            elif mode == "metro":
                # Metro routes can travel on metro links (fast), transfer walking edges, and walk along roads (slow) to transfer
                if etype == "metro":
                    line = edge_attr["line"]
                    if line in self.disabled_metro_lines:
                        return 1e9
                    return edge_attr["length"] / METRO_SPEED
                elif etype == "transfer":
                    return edge_attr["length"] / WALK_SPEED
                elif etype == "road":
                    # Walking to transfer
                    return edge_attr["length"] / WALK_SPEED
                return 1e9

            elif mode == "bus":
                # Buses travel along roads. If edge has a bus line tag, it's cheap (transit speed)
                # Else they walk to connect (transfer)
                if etype == "road":
                    if edge_attr.get("bus_route"):
                        # Travel by bus
                        return edge_attr["length"] / BUS_BASE_SPEED
                    else:
                        # Walk
                        return edge_attr["length"] / WALK_SPEED
                return 1e9

            elif mode == "bike_share":
                # Bike-share uses road network at slightly slower bike speed
                if etype != "road":
                    return 1e9
                rain_penalty = 1.0 + 0.5 * self.weather_rain_intensity
                # Add ~2 min docking overhead amortised per edge
                docking_overhead = 120.0 / max(1, len(self.g.edges))  # seconds per edge
                return (
                    edge_attr["length"] / BIKE_SHARE_SPEED
                ) * rain_penalty + docking_overhead

            elif mode == "e_rickshaw":
                # E-rickshaws use road network, subject to lighter congestion
                if etype != "road":
                    return 1e9
                # Lighter BPR impact: e-rickshaws are smaller vehicles
                length = edge_attr["length"]
                speed = E_RICKSHAW_SPEED * (1.0 - 0.20 * self.weather_rain_intensity)
                t_zero = length / max(1.0, speed)
                flow = edge_attr.get("flow", 0)
                capacity = edge_attr.get("capacity", 100.0)
                # Lighter congestion sensitivity (alpha=0.10)
                congestion_term = min(5.0, 0.10 * ((flow / max(10.0, capacity)) ** 3.0))
                return t_zero * (1.0 + congestion_term)

            return 1e9

        try:
            path = nx.dijkstra_path(self.g, source, target, weight=weight_func)
            self._routing_cache[cache_key] = path
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self._routing_cache[cache_key] = None
            return None

    def calculate_path_travel_time(self, path: list[str], mode: str) -> float:
        """Sum travel times over a path for a specific mode."""
        if not path or len(path) < 2:
            return 0.0

        total_time = 0.0
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            if self.g.has_edge(u, v):
                edge_data = self.g.edges[u, v]

                # Define weight
                etype = edge_data["type"]
                if mode == "walk":
                    t = edge_data["length"] / WALK_SPEED
                elif mode == "bike":
                    t = (edge_data["length"] / BIKE_SPEED) * (
                        1.0 + 0.5 * self.weather_rain_intensity
                    )
                elif mode in ("car", "auto"):
                    t = self.compute_bpr_travel_time(u, v, edge_data)
                elif mode == "metro":
                    if etype == "metro":
                        t = edge_data["length"] / METRO_SPEED
                    elif etype == "transfer":
                        t = edge_data["length"] / WALK_SPEED
                    else:
                        t = edge_data["length"] / WALK_SPEED
                elif mode == "bus":
                    if etype == "road" and edge_data.get("bus_route"):
                        t = edge_data["length"] / BUS_BASE_SPEED
                    else:
                        t = edge_data["length"] / WALK_SPEED
                elif mode == "bike_share":
                    rain_penalty = 1.0 + 0.5 * self.weather_rain_intensity
                    t = (edge_data["length"] / BIKE_SHARE_SPEED) * rain_penalty
                elif mode == "e_rickshaw":
                    speed = E_RICKSHAW_SPEED * (
                        1.0 - 0.20 * self.weather_rain_intensity
                    )
                    t = edge_data["length"] / max(1.0, speed)
                else:
                    t = edge_data["length"] / WALK_SPEED

                total_time += t
            else:
                # Fallback if graph is missing edge
                total_time += 10.0
        return total_time / 60.0  # return minutes

    def update_road_congestion(self, active_commuters: list) -> None:
        """Reset flow and count active agents on each road segment, and invalidate the routing cache."""
        # Reset edge flows
        for u, v in self.g.edges:
            self.g.edges[u, v]["flow"] = 0

        # Increment flows for agents currently on road segments
        for agent in active_commuters:
            if agent.current_route and agent.route_index < len(agent.current_route) - 1:
                idx = agent.route_index
                u = agent.current_route[idx]
                v = agent.current_route[idx + 1]
                if self.g.has_edge(u, v) and self.g.edges[u, v]["type"] == "road":
                    self.g.edges[u, v]["flow"] += 1

        # Clear routing cache as congestion and travel times have changed for the next tick
        self.clear_routing_cache()
