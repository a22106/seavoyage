# MNetwork.py
import os
import geojson
import networkx as nx
import numpy as np
from shapely import LineString
from sklearn.neighbors import NearestNeighbors
from scipy.spatial import Delaunay
from typing import Optional, Dict, List, Tuple, Any, Union

from searoute import Marnet
from searoute.utils import distance
from seavoyage.modules.restriction import CustomRestriction
from seavoyage.utils.coordinates import decdeg_to_degmin
from seavoyage.utils.shapely_utils import is_valid_edge
from seavoyage.log import logger
from searoute.classes.passages import Passage
from seavoyage.exceptions import (
    UnreachableDestinationError, 
    StartInRestrictionError, 
    DestinationInRestrictionError,
    IsolatedOriginError
)
from seavoyage.utils.shoreline import shoreline

class MNetwork(Marnet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Custom restriction zones storage dictionary
        self.custom_restrictions: Dict[str, CustomRestriction] = {}
        # Store initial restriction zones state
        self._initial_restrictions: List[Passage] = [Passage.northwest]

    def reset_restrictions(self) -> None:
        """
        Reset all restriction zones to initial state.
        Remove all custom restriction zones and 
        restore default restriction zones to initial state.
        """
        # Reset default restriction zones
        self.restrictions = self._initial_restrictions.copy() if hasattr(self, '_initial_restrictions') else []
        
        # Reset custom restriction zones
        self.custom_restrictions.clear()
        
        logger.debug(f"Restriction zones reset: default={self.restrictions}, custom={list(self.custom_restrictions.keys())}")
        
    def save_initial_state(self) -> None:
        """
        Save current default restriction zones state as initial state.
        """
        self._initial_restrictions = self.restrictions.copy() if hasattr(self, 'restrictions') else []
        logger.debug(f"Initial restriction zones state saved: {self._initial_restrictions}")

    def add_node_with_edges(
        self, 
        node: Tuple[float, float], 
        threshold: float = 100.0, 
        land_polygon: Optional[Any] = None
    ) -> List[Tuple[Tuple[float, float], Tuple[float, float], float]]:
        """
        Add a new node and automatically create edges with existing nodes within threshold.
        
        Args:
            node: (longitude, latitude) coordinates of node to add
            threshold: Distance threshold (km) for edge creation
            land_polygon: Land polygon (shapely MultiPolygon)
            
        Returns:
            List of created edges [(node1, node2, weight), ...]
        """
        if threshold <= 0 or not isinstance(threshold, (int, float)):
            raise ValueError("Threshold must be a positive number.")
        
        if not isinstance(node, tuple) or len(node) != 2:
            raise TypeError("Node must be a tuple of (longitude, latitude).")
        
        if node in self.nodes:
            return []
        
        # Add node
        self.add_node(node)
        
        # List to store created edges
        created_edges: List[Tuple[Tuple[float, float], Tuple[float, float], float]] = []
        
        # Calculate distances to existing nodes and create edges within threshold
        for existing_node in list(self.nodes):
            if existing_node == node:
                continue
                
            dist = distance(node, existing_node, units="km")
            if dist <= threshold:
                # If land polygon is provided, check if edge crosses land
                if land_polygon:
                    line = LineString([node, existing_node])
                    if not is_valid_edge(line, land_polygon):
                        continue
                
                self.add_edge(node, existing_node, weight=dist)
                created_edges.append((node, existing_node, dist))
                
        return created_edges

    # add_node_and_connect ------------------------------------
    # TODO: Fix KNN not being applied issue
    def add_node_and_connect(
        self,
        new_node: Tuple[float, float],
        k: int = 5,
        land_polygon = shoreline,
    ):
        # 0) Normalize longitude (optional) + register node
        new_node = self._norm_coord(new_node)
        if new_node not in self:
            self.add_node(new_node)

        created_edges: list[tuple] = []
        coords = np.array(list(self.nodes))

        if len(coords) <= 1:
            self.update_kdtree()
            return created_edges

        # 1) KNN ------------------------------------------------------
        coords_aug, idx_map = self._augment_coords(coords)
        new_node_aug = np.array(new_node)          # Same coordinate system

        nbrs = NearestNeighbors(
            n_neighbors=min(k + 1, len(coords_aug)),
            algorithm="ball_tree",
        ).fit(coords_aug)

        dists, inds = nbrs.kneighbors([new_node_aug])

        for aug_idx in inds[0][1:]:                # Exclude self
            neighbor = tuple(coords[idx_map[aug_idx]])
            if neighbor == new_node:               # Skip same node
                continue

            line = LineString([new_node, neighbor])
            if land_polygon and not is_valid_edge(line, land_polygon):
                continue

            w = float(distance(new_node, neighbor, units="km"))
            if not self.has_edge(new_node, neighbor):
                self.add_edge(new_node, neighbor, weight=w)
                created_edges.append((new_node, neighbor, w))

        # 2) Delaunay -------------------------------------------------
        if len(coords) >= 3:
            coords_with_new = np.vstack([coords, new_node])  # Original coordinates only
            try:
                tri = Delaunay(coords_with_new)
                idx_new = len(coords_with_new) - 1

                for simplex in tri.simplices:
                    if idx_new not in simplex:
                        continue
                    for i in range(3):
                        for j in range(i + 1, 3):
                            a, b = simplex[i], simplex[j]
                            if idx_new not in (a, b):
                                continue
                            n1 = tuple(coords_with_new[a])
                            n2 = tuple(coords_with_new[b])

                            if self.has_edge(n1, n2):
                                continue
                            line = LineString([n1, n2])
                            if land_polygon and not is_valid_edge(line, land_polygon):
                                continue

                            w = float(distance(n1, n2, units="km"))
                            self.add_edge(n1, n2, weight=w)
                            created_edges.append((n1, n2, w))
            except Exception as e:
                logger.error(f"Delaunay error: {e}")

        # 3) Finalization ----------------------------------------------------
        self.update_kdtree()
        logger.info(f"Created {len(created_edges)} new edges")
        return created_edges


    def add_nodes_with_edges(self, nodes: list[tuple[float, float]], threshold: float = 100.0, land_polygon = None):
        """
        Add multiple nodes and automatically create edges with all nodes (existing + new) within threshold.

        :param nodes: List of node coordinates [(longitude, latitude), ...] to add
        :param threshold: Distance threshold (km) for edge creation
        :param land_polygon: Land polygon (shapely MultiPolygon)
        :return: List of created edges [(node1, node2, weight), ...]
        """
        if not isinstance(nodes, list):
            raise TypeError("Nodes must be a list of tuples representing the coordinates.")
        if threshold <= 0 or not isinstance(threshold, (int, float)):
            raise ValueError("Threshold must be a positive number.")
        
        if any(not isinstance(node, tuple) or len(node) != 2 for node in nodes):
            raise TypeError("Each node must be a tuple of (longitude, latitude).")
        
        all_created_edges = []
        
        # Process each new node
        for node in nodes:
            # Create edges with existing nodes (including land crossing check)
            edges = self.add_node_with_edges(node, threshold, land_polygon)
            all_created_edges.extend(edges)
            
            # Create edges with already added new nodes (no land crossing check)
            for other_node in nodes:
                if other_node == node or other_node not in self.nodes:
                    continue
                    
                dist = distance(node, other_node, units="km")
                if dist <= threshold:
                    self.add_edge(node, other_node, weight=dist)
                    all_created_edges.append((node, other_node, dist))
                    
        logger.debug(f"Added {len(all_created_edges)} edges")
        return all_created_edges

    def _extract_point_coordinates(self, point: geojson.Point):
        """
        Extract coordinates from a GeoJSON Point object.

        :param point: Point object to extract coordinates from
        :return: (longitude, latitude) coordinates
        """
        if isinstance(point, dict):
            coords = point["coordinates"]
        elif isinstance(point, geojson.Point):
            coords = point.coordinates
        else:
            raise TypeError("Invalid point type. Must be a geojson.Point or dict.")
        
        if not coords or len(coords) < 2:
            raise ValueError("Invalid point coordinates")
        
        return tuple(coords[:2])  # (longitude, latitude)
    
    def add_geojson_point(self, point, threshold: float = 100.0):
        """
        Add a GeoJSON Point object as node and create edges with nodes within threshold.
        :param point: Point object to add
        :param threshold: Distance threshold (km) for edge creation
        :return: List of created edges
        """
        coords = self._extract_point_coordinates(point)
        return self.add_node_with_edges(coords, threshold)

    def add_geojson_multipoint(self, multipoint, threshold: float = 100.0):
        """
        Add all points from a GeoJSON MultiPoint object as nodes and create edges with nodes within threshold.
        :param multipoint: MultiPoint object to add
        :param threshold: Distance threshold (km) for edge creation
        :return: List of created edges
        """
        #TODO: Optimization needed
        if isinstance(multipoint, dict):
            coords = multipoint.get('coordinates', [])
        else:
            coords = multipoint.coordinates
            
        nodes = [tuple(coord[:2]) for coord in coords]
        return self.add_nodes_with_edges(nodes, threshold)

    def add_geojson_feature_collection(self, feature_collection, threshold: float = 100.0, land_polygon = None):
        """
        Add Point and LineString features from a GeoJSON FeatureCollection as nodes and edges.
        :param feature_collection: FeatureCollection object containing Point or LineString features
        :param threshold: Distance threshold (km) for edge creation
        :param land_polygon: Land polygon (shapely MultiPolygon)
        :return: List of created edges
        """
        if isinstance(feature_collection, dict):
            features = feature_collection.get('features', [])
        else:
            features = feature_collection.features

        nodes = []
        direct_edges = []  # List to store edges extracted directly from LineString
        
        for feature in features:
            if isinstance(feature, dict):
                geometry = feature.get('geometry', {})
                properties = feature.get('properties', {})
                
                if geometry.get('type') == 'Point':
                    coords = geometry.get('coordinates')
                    if coords and len(coords) >= 2:
                        nodes.append((coords[0], coords[1]))
                        
                elif geometry.get('type') == 'LineString':
                    # Process LineString
                    coords = geometry.get('coordinates')
                    if coords and len(coords) >= 2:
                        # Add each coordinate in LineString as node
                        line_nodes = [(coord[0], coord[1]) for coord in coords]
                        nodes.extend(line_nodes)
                        
                        # Create direct edges between consecutive coordinates in LineString
                        for i in range(len(line_nodes) - 1):
                            node1 = line_nodes[i]
                            node2 = line_nodes[i + 1]
                            
                            # Calculate weight (from properties or distance calculation)
                            if 'weight' in properties:
                                weight = properties['weight']
                            else:
                                weight = distance(node1, node2, units="km")
                                
                            direct_edges.append((node1, node2, weight, properties))
            else:
                geometry = feature.geometry
                properties = feature.properties if hasattr(feature, 'properties') else {}
                
                if isinstance(geometry, geojson.Point):
                    coords = geometry.coordinates
                    if coords and len(coords) >= 2:
                        nodes.append((coords[0], coords[1]))
                        
                elif isinstance(geometry, geojson.LineString):
                    # Process LineString
                    coords = geometry.coordinates
                    if coords and len(coords) >= 2:
                        # Add each coordinate in LineString as node
                        line_nodes = [(coord[0], coord[1]) for coord in coords]
                        nodes.extend(line_nodes)
                        
                        # Create direct edges between consecutive coordinates in LineString
                        for i in range(len(line_nodes) - 1):
                            node1 = line_nodes[i]
                            node2 = line_nodes[i + 1]
                            
                            # Calculate weight (from properties or distance calculation)
                            if hasattr(properties, 'weight') or (isinstance(properties, dict) and 'weight' in properties):
                                weight = properties.get('weight') if isinstance(properties, dict) else properties.weight
                            else:
                                weight = distance(node1, node2, units="km")
                                
                            direct_edges.append((node1, node2, weight, properties))
        
        # Add nodes and create edges within threshold
        all_created_edges = self.add_nodes_with_edges(nodes, threshold, land_polygon)
        
        # Add edges extracted directly from LineString
        for node1, node2, weight, props in direct_edges:
            if node1 in self.nodes and node2 in self.nodes:
                # If land polygon is provided, check if edge crosses land
                if land_polygon:
                    line = LineString([node1, node2])
                    if not is_valid_edge(line, land_polygon):
                        continue
                
                # Set edge attributes
                edge_attrs = {'weight': weight}
                
                # Add other properties to edge attributes
                if isinstance(props, dict):
                    for key, value in props.items():
                        if key != 'weight':  # Avoid duplicate weight
                            edge_attrs[key] = value
                
                # Add edge
                self.add_edge(node1, node2, **edge_attrs)
                all_created_edges.append((node1, node2, weight))
        
        logger.debug(f"Total {len(all_created_edges)} edges added")
        return all_created_edges
    
    def to_geojson(self, file_path: Optional[str] = None) -> geojson.FeatureCollection:
        """Export nodes and edges to GeoJSON format."""
        features = []
        
        for u, v, attrs in self.edges(data=True):
            line = geojson.LineString([[u[0], u[1]], [v[0], v[1]]])
            feature = geojson.Feature(geometry=line, properties=attrs)
            features.append(feature)
            
        feature_collection = geojson.FeatureCollection(features)
        
        if file_path:
            with open(file_path, "w") as f:
                geojson.dump(feature_collection, f)
                
        return feature_collection
    
    def to_line_string(self) -> List[LineString]:
        """Export nodes and edges as LineString objects."""
        linestrings = []
        for u, v, attrs in self.edges(data=True):
            linestrings.append(LineString([[u[0], u[1]], [v[0], v[1]]]))
        return linestrings
    
    @classmethod
    def from_geojson(cls, *args):
        """
        Create MNetwork object from GeoJSON file path or GeoJSON object.
        
        Parameters
        ----------
        *args : File path or GeoJSON object
            - string: Interpreted as GeoJSON file path
            - dict: Interpreted as GeoJSON object (dictionary)
            - geojson.GeoJSON: Interpreted as GeoJSON object
            
        Returns
        -------
        MNetwork object
        """
        mnetwork = cls()
        mnetwork = mnetwork.load_from_geojson(*args)
        mnetwork.update_kdtree()
        return mnetwork

    @staticmethod
    def _norm_coord(coord: Tuple[float, float]) -> Tuple[float, float]:
        """Normalize coordinates to [-180, 180) range."""
        lon, lat = coord
        lon = (lon + 180.0) % 360.0 - 180.0   # -180 ~ <180
        return lon, lat

    def load_from_geojson(self, *args):
        """
        Load graph from GeoJSON file path or GeoJSON object.
        Supports Polygon, MultiPolygon and normalizes all longitudes to [-180, 180) range
        to prevent dateline issues.
        """
        # -- Internal utilities --────────
        def _fix_coords(coords):
            """
            Recursively traverse coordinate array and normalize (lon, lat) tuples
            using self._norm_coord() then return as list
            """
            if coords is None:
                return coords

            # Single point [lon, lat]
            if isinstance(coords[0], (int, float)):
                return list(self._norm_coord(tuple(coords)))

            # Nested list [[...], [...]]
            return [_fix_coords(c) for c in coords]

        def _cast_dict_to_geo(obj_dict):
            """Convert dict to geojson object (LineString etc)"""
            gtype = obj_dict.get("type")
            return {
                "LineString":    geojson.LineString,
                "MultiLineString": geojson.MultiLineString,
                "Point":         geojson.Point,
                "MultiPoint":    geojson.MultiPoint,
                "Polygon":       geojson.Polygon,
                "MultiPolygon":  geojson.MultiPolygon,
            }.get(gtype, geojson.GeoJSON)(obj_dict["coordinates"])

        # ── Main body ────────────────────────────────────────────────
        for arg in args:
            # 1) Load file path or object ---------------------------------
            if isinstance(arg, str):
                if not os.path.exists(arg):
                    raise FileNotFoundError(f"GeoJSON file not found: {arg}")
                with open(arg, "r") as f:
                    data = geojson.load(f)
            elif isinstance(arg, (dict, geojson.base.GeoJSON)):
                data = arg
            else:
                raise TypeError("Only str path or GeoJSON/dict allowed")

            # 2) Normalize coordinates & apply to graph -----------------------------
            def handle_geometry(geometry, properties):
                # Convert dict → geojson object
                if isinstance(geometry, dict):
                    geometry = _cast_dict_to_geo(geometry)

                # Normalize coordinates
                geometry["coordinates"] = _fix_coords(geometry["coordinates"])

                # Same as existing logic afterwards --------------------------------
                gtype = geometry.type
                if gtype == "LineString":
                    coords = geometry.coordinates
                    for u, v in zip(coords[:-1], coords[1:]):
                        self.add_edge(tuple(u), tuple(v), **properties)
                        self.add_edge(tuple(v), tuple(u), **properties)
                elif gtype == "MultiLineString":
                    for line in geometry.coordinates:
                        for u, v in zip(line[:-1], line[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            self.add_edge(tuple(v), tuple(u), **properties)
                elif gtype == "Point":
                    self.add_node(tuple(geometry.coordinates), **properties)
                elif gtype == "MultiPoint":
                    for pt in geometry.coordinates:
                        self.add_node(tuple(pt), **properties)
                elif gtype == "Polygon":
                    outer = geometry.coordinates[0]
                    for u, v in zip(outer[:-1], outer[1:]):
                        self.add_edge(tuple(u), tuple(v), **properties)
                        self.add_edge(tuple(v), tuple(u), **properties)
                    if outer[0] != outer[-1]:
                        self.add_edge(tuple(outer[-1]), tuple(outer[0]), **properties)
                        self.add_edge(tuple(outer[0]), tuple(outer[-1]), **properties)
                elif gtype == "MultiPolygon":
                    for poly in geometry.coordinates:
                        outer = poly[0]
                        for u, v in zip(outer[:-1], outer[1:]):
                            self.add_edge(tuple(u), tuple(v), **properties)
                            self.add_edge(tuple(v), tuple(u), **properties)
                        if outer[0] != outer[-1]:
                            self.add_edge(tuple(outer[-1]), tuple(outer[0]), **properties)
                            self.add_edge(tuple(outer[0]), tuple(outer[-1]), **properties)
                else:
                    logger.debug(f"Unsupported geometry type: {gtype}")

            # 3) Distinguish Feature / FeatureCollection -----------------------
            dtype = data["type"] if isinstance(data, dict) else data.type
            if dtype == "FeatureCollection":
                # CRS
                crs_name = (data.get("crs", {})
                               .get("properties", {})
                               .get("name")) if isinstance(data, dict) else \
                           (getattr(getattr(data, "crs", None), "properties", None)
                               or {}).get("name")
                if crs_name:
                    self.graph["crs"] = crs_name

                feats = data["features"] if isinstance(data, dict) else data.features
                for feat in feats:
                    geom = feat["geometry"] if isinstance(feat, dict) else feat.geometry
                    props = feat.get("properties", {}) if isinstance(feat, dict) else feat.properties
                    handle_geometry(geom, props)
            elif dtype == "Feature":
                geom = data["geometry"] if isinstance(data, dict) else data.geometry
                props = data.get("properties", {}) if isinstance(data, dict) else data.properties
                handle_geometry(geom, props)
            else:  # Standalone geometry
                handle_geometry(data, {})

        # 4) Update KD-Tree ---------------------------------------------
        self.update_kdtree()
        return self
    
    @classmethod
    def from_networkx(cls, graph: nx.Graph):
        """
        Convert a NetworkX graph to an MNetwork object.
        :param graph: NetworkX graph
        :return: MNetwork object
        """
        mnetwork = cls()
        # Add all nodes
        for node, attrs in graph.nodes(data=True):
            # Check if node is a tuple in (longitude, latitude) format
            if isinstance(node, tuple) and len(node) >= 2:
                mnetwork.add_node(node, **attrs)
            else:
                # If node is not in coordinate format, check if it has x and y attributes
                if 'x' in attrs and 'y' in attrs:
                    coords = (attrs['x'], attrs['y'])
                    mnetwork.add_node(coords, **{k: v for k, v in attrs.items() if k not in ['x', 'y']})
                else:
                    logger.debug(f"Skipping node {node} - no coordinate information")
        
        # Add all edges
        for u, v, attrs in graph.edges(data=True):
            # Handle case when nodes in original graph are not in coordinate format
            u_node = u
            v_node = v
            
            if not isinstance(u, tuple) and u in graph:
                attrs_u = graph.nodes[u]
                if 'x' in attrs_u and 'y' in attrs_u:
                    u_node = (attrs_u['x'], attrs_u['y'])
            
            if not isinstance(v, tuple) and v in graph:
                attrs_v = graph.nodes[v]
                if 'x' in attrs_v and 'y' in attrs_v:
                    v_node = (attrs_v['x'], attrs_v['y'])
            
            # Add edge only when both nodes are in coordinate format
            if isinstance(u_node, tuple) and isinstance(v_node, tuple):
                mnetwork.add_edge(u_node, v_node, **attrs)
            else:
                logger.debug(f"Skipping edge {u}-{v} - no coordinate information")
        
        # Copy graph attributes
        for key, value in graph.graph.items():
            mnetwork.graph[key] = value
        
        # Update KDTree
        mnetwork.update_kdtree()
        
        return mnetwork
    
    @classmethod
    def from_marnet(cls, marnet_obj: "Marnet") -> "MNetwork":
        """Convert existing Marnet object to MNetwork object"""
        if not isinstance(marnet_obj, Marnet):
            raise TypeError("marnet_obj must be an instance of Marnet")

        mnetwork = cls.from_networkx(marnet_obj)

        mnetwork.restrictions = list(getattr(marnet_obj, "restrictions", []))
        mnetwork.custom_restrictions = dict(
            getattr(marnet_obj, "custom_restrictions", {})
        )

        mnetwork.update_kdtree()

        return mnetwork
    
    def add_restriction(self, restriction: CustomRestriction):
        """
        Add custom restriction zone
        
        Args:
            restriction: CustomRestriction object
        """
        self.custom_restrictions[restriction.name] = restriction
        logger.debug(f"Restriction added: {restriction.name}")
        
    def remove_restriction(self, name: str):
        """
        Remove custom restriction zone
        
        Args:
            name: Restriction zone name
        """
        if name in self.custom_restrictions:
            del self.custom_restrictions[name]
    
    def _filter_custom_restricted_edge(self, u, v, data):
        """Filter edges that intersect with custom restriction zones"""
        # Convert edge to LineString
        line = LineString([u, v])
        
        # Filter existing restriction zones 
        restrictions_passed = data.get('passage')
        logger.debug(f"Edge {u} -> {v} passage information: {restrictions_passed}")
        
        if isinstance(restrictions_passed, str):
            # Single passage case
            if restrictions_passed in self.restrictions:
                logger.debug(f"Edge {u} -> {v} intersects with default restriction zone '{restrictions_passed}'")
                return False
        elif isinstance(restrictions_passed, list):
            # Multiple passages case, filter if any passage corresponds to restriction zone
            for passage in restrictions_passed:
                if passage in self.restrictions:
                    logger.debug(f"Edge {u} -> {v} intersects with default restriction zone '{passage}'")
                    return False
        
        # Filter custom restriction zones
        for name, restriction in self.custom_restrictions.items():
            # Case when line segment intersects or is completely contained within restriction zone
            if restriction.polygon.intersects(line) or restriction.polygon.contains(line):
                logger.debug(f"Edge {u} -> {v} intersects or is contained within custom restriction zone '{name}'")
                return False
                
        # Case when edge does not pass through any restriction zones
        logger.debug(f"Edge {u} -> {v} does not pass through any restriction zones")
        return True
    
    def is_point_in_restriction(self, point: tuple) -> tuple[bool, Optional[str]]:
        """
        Check if a given point is within restriction zones.
        
        Args:
            point: (longitude, latitude) coordinates
            
        Returns:
            tuple[bool, Optional[str]]: (True if point is within restriction zone, restriction zone name) or (False, None)
        """
        # Explicitly specify the type of custom_restrictions
        restrictions: dict[str, CustomRestriction] = self.custom_restrictions
        for name, restriction in restrictions.items():
            if restriction.contains_point(point):
                return True, name
        return False, None
    
    def shortest_path(self, origin, destination, method = "astar") -> list:
        """
        Calculate shortest path between origin and destination while avoiding restriction zones
        
        Args:
            origin: Origin coordinates (longitude, latitude)
            destination: Destination coordinates (longitude, latitude)
            method: Path finding method (default: "dijkstra", "astar" also available)
        Returns:
            List: List of nodes in shortest path
            
        Raises:
            ValueError: When algorithm is not 'dijkstra' or 'astar'
            UnreachableDestinationError: When destination cannot be reached due to restriction zones
            StartInRestrictionError: When origin is within restriction zone
            DestinationInRestrictionError: When destination is within restriction zone
            IsolatedOriginError: When origin is isolated by restriction zones
        """
        # Add debugging logs
        logger.debug(f"Origin coordinates: {origin}, destination coordinates: {destination}")
        logger.debug(f"Currently applied default restriction zones: {self.restrictions}")
        logger.debug(f"Currently applied custom restriction zones: {list(self.custom_restrictions.keys())}")
        
        # Check if origin is in restriction zone
        is_origin_restricted, origin_restriction = self.is_point_in_restriction(origin)
        if is_origin_restricted:
            logger.debug(f"Origin {decdeg_to_degmin(origin)} is within restriction zone '{origin_restriction}'")
            raise StartInRestrictionError(origin, origin_restriction)
            
        # Check if destination is in restriction zone
        is_dest_restricted, dest_restriction = self.is_point_in_restriction(destination)
        if is_dest_restricted:
            logger.debug(f"Destination {decdeg_to_degmin(destination)} is within restriction zone '{dest_restriction}'")
            raise DestinationInRestrictionError(destination, dest_restriction)
        
        if method not in ("dijkstra", "astar"):
            raise ValueError("Method must be either 'dijkstra' or 'astar'.")
        
        # Find nearest nodes from KDTree
        origin_node = self.kdtree.query(origin)
        destination_node = self.kdtree.query(destination)
        
        # Check if line segment between origin and KDTree-found node passes through restriction zones
        if origin != origin_node:  # When origin and network node are different
            line_to_origin = LineString([origin, origin_node])
            logger.debug(f"Nearest network node from origin {origin}: {origin_node}")
            
            # Check custom restriction zones
            for name, restriction in self.custom_restrictions.items():
                if restriction.polygon.intersects(line_to_origin):
                    logger.debug(f"Path from origin {origin} to nearest node {origin_node} intersects with restriction zone '{name}'")
                    raise IsolatedOriginError(origin, [name])
        
        # Log neighbor node count
        neighbors = list(self.neighbors(origin_node))
        logger.debug(f"Number of neighbor nodes for origin node {origin_node}: {len(neighbors)}")
        
        # Weight function considering custom restriction zones
        def custom_weight(u, v, data):
            is_valid = self._filter_custom_restricted_edge(u, v, data)
            if is_valid:
                weight = distance(u, v)
                return data.get('weight', weight)
            else:
                return float('inf')
        
        # Check if origin node is isolated
        is_isolated = True
        logger.debug(f"Starting isolation check for origin node {origin_node}")
        
        for neighbor in neighbors:
            edge_data = self.get_edge_data(origin_node, neighbor)
            is_valid_edge = self._filter_custom_restricted_edge(origin_node, neighbor, edge_data)
            logger.debug(f"  - Neighbor node {neighbor}: valid path = {is_valid_edge}")
            
            if is_valid_edge:
                is_isolated = False
                break
        
        if is_isolated:
            logger.debug(f"Origin {origin} is isolated by restriction zones")
            restriction_names = list(self.custom_restrictions.keys())
            if self.restrictions:
                restriction_names.extend([str(r) for r in self.restrictions])
            raise IsolatedOriginError(origin, restriction_names)
        
        try:
            if method == "dijkstra":
                result = nx.shortest_path(self, origin_node, destination_node, weight=custom_weight)
            elif method == "astar":
                result = nx.astar_path(self, origin_node, destination_node, weight=custom_weight)
            logger.debug(f"Path finding successful: {len(result)} nodes")
            return result
        except nx.NetworkXNoPath:
            # When NetworkX cannot find a path
            logger.debug(f"Cannot find path: {origin} -> {destination}")
            restriction_names = list(self.custom_restrictions.keys())
            if self.restrictions:
                restriction_names.extend([str(r) for r in self.restrictions])
            raise UnreachableDestinationError(origin, destination, restriction_names)
        
    # ① Longitude duplication helper ------------------------------------------
    @staticmethod
    def _augment_coords(coords: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        coords: (N,2)  [lon, lat]
        return:
            coords_aug : (3N,2)  Expanded with longitude ±360°
            idx_map    : (3N,)   Original coordinate index that each duplicated row points to
        """
        lons, lats = coords[:, 0], coords[:, 1]
        coords_minus = np.column_stack((lons - 360.0, lats))
        coords_plus  = np.column_stack((lons + 360.0, lats))

        coords_aug = np.vstack([coords, coords_minus, coords_plus])
        idx_map    = np.tile(np.arange(len(coords)), 3)

        return coords_aug, idx_map