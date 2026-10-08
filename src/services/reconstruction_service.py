import os
import re
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, LineString, MultiPolygon
import streamlit as st

try:
    import pygplates
    HAS_PYGPLATES = True
except ImportError:
    HAS_PYGPLATES = False


class ReconstructionService:
    """Service dedicated to generating precomputed coordinate NPZ archives and extracting/rotating GPML country boundary features."""

    def __init__(
        self,
        rotations_dir: str = os.path.join("data", "rotations"),
        reconstructions_dir: str = os.path.join("data", "reconstructions"),
    ):
        self.rotations_dir = rotations_dir
        self.reconstructions_dir = reconstructions_dir
        self.rot_file = self._resolve_file("PALEOMAP_PlateModel.rot")
        self.gpml_file = self._resolve_file("PALEOMAP_StaticPolygons.gpml")
        self.gpml_boundaries_file = self._resolve_file("PALEOMAP_PoliticalBoundaries.gpml")

    def _resolve_file(self, filename: str) -> str:
        """Helper to resolve file paths across potential data subdirectories dynamically."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [
            os.path.join(self.reconstructions_dir, filename),
            os.path.join(self.rotations_dir, filename),
            os.path.join("data", "raw", filename),
            os.path.join("data", filename),
            os.path.join(base_dir, "data", "reconstructions", filename),
            os.path.join(base_dir, "data", "rotations", filename),
            os.path.join(base_dir, "data", "raw", filename),
            os.path.join(base_dir, "data", filename),
        ]
        return next((p for p in candidates if os.path.exists(p)), os.path.join(self.rotations_dir, filename))

    def has_required_files(self) -> bool:
        """Checks if both required PALEOMAP rotation files are present."""
        rot_path = self._resolve_file("PALEOMAP_PlateModel.rot")
        gpml_path = self._resolve_file("PALEOMAP_StaticPolygons.gpml")
        return os.path.exists(rot_path) and os.path.exists(gpml_path)

    @staticmethod
    @st.cache_data
    def load_plate_rotations_cache() -> dict:
        """Loads precomputed plate rotation Euler poles from local JSON archive."""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        possible_paths = [
            os.path.join("data", "processed", "plate_rotations.json"),
            os.path.join("data", "plate_rotations.json"),
            os.path.join(base_dir, "data", "processed", "plate_rotations.json"),
            os.path.join(base_dir, "data", "plate_rotations.json"),
            "plate_rotations.json"
        ]
        json_path = next((p for p in possible_paths if os.path.exists(p)), None)
        if json_path:
            try:
                with open(json_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def rotate_coords_rodrigues(coords_list: list, pole_lat: float, pole_lon: float, angle_deg: float) -> list:
        """Rotates spherical coordinates (lon, lat) using Rodrigues 3D rotation formula."""
        if angle_deg == 0.0 or not coords_list:
            return coords_list

        lat_p, lon_p = np.radians(pole_lat), np.radians(pole_lon)
        theta = np.radians(angle_deg)

        u = np.array([
            np.cos(lat_p) * np.cos(lon_p),
            np.cos(lat_p) * np.sin(lon_p),
            np.sin(lat_p)
        ], dtype=np.float64)

        coords_arr = np.array(coords_list, dtype=np.float64)
        lons = np.radians(coords_arr[:, 0])
        lats = np.radians(coords_arr[:, 1])

        vx = np.cos(lats) * np.cos(lons)
        vy = np.cos(lats) * np.sin(lons)
        vz = np.sin(lats)
        v = np.column_stack([vx, vy, vz])

        cos_t = np.cos(theta)
        sin_t = np.sin(theta)

        u_cross_v = np.cross(u, v)
        u_dot_v = np.dot(v, u)

        v_rot = (v * cos_t) + (u_cross_v * sin_t) + (u[np.newaxis, :] * u_dot_v[:, np.newaxis] * (1.0 - cos_t))

        norm = np.linalg.norm(v_rot, axis=1, keepdims=True)
        norm[norm == 0] = 1.0
        v_rot = v_rot / norm

        lat_rot = np.degrees(np.arcsin(np.clip(v_rot[:, 2], -1.0, 1.0)))
        lon_rot = np.degrees(np.arctan2(v_rot[:, 1], v_rot[:, 0]))

        return list(zip(lon_rot, lat_rot))

    @staticmethod
    def rotate_geometry(geom, pole_lat: float, pole_lon: float, angle_deg: float):
        """Recursively rotates Shapely Polygon, LineString, or MultiPolygon geometry objects."""
        if angle_deg == 0.0 or geom is None:
            return geom

        if geom.geom_type == "Polygon":
            new_ext = ReconstructionService.rotate_coords_rodrigues(list(geom.exterior.coords), pole_lat, pole_lon, angle_deg)
            new_interiors = [
                ReconstructionService.rotate_coords_rodrigues(list(interior.coords), pole_lat, pole_lon, angle_deg)
                for interior in geom.interiors
            ]
            return Polygon(new_ext, new_interiors)
        elif geom.geom_type == "LineString":
            new_coords = ReconstructionService.rotate_coords_rodrigues(list(geom.coords), pole_lat, pole_lon, angle_deg)
            return LineString(new_coords)
        elif geom.geom_type == "MultiPolygon":
            polys = [ReconstructionService.rotate_geometry(poly, pole_lat, pole_lon, angle_deg) for poly in geom.geoms]
            return MultiPolygon(polys)
        return geom

    def get_available_countries(self) -> list[str]:
        """Returns sorted list of available country names from GPML political boundaries file."""
        gpml_path = self._resolve_file("PALEOMAP_PoliticalBoundaries.gpml")
        return self._extract_available_countries(gpml_path)

    @staticmethod
    @st.cache_data
    def _extract_available_countries(gpml_path: str) -> list[str]:
        if not os.path.exists(gpml_path):
            return []

        tree = ET.parse(gpml_path)
        root = tree.getroot()
        namespaces = {
            "gpml": "http://www.gplates.org/gplates",
            "gml": "http://www.opengis.net/gml",
        }

        countries = set()
        for feature in root.findall(".//gpml:UnclassifiedFeature", namespaces):
            name_elem = feature.find('.//gpml:key[.="NAME"]/../gpml:value', namespaces)
            if name_elem is not None and name_elem.text:
                c_name = name_elem.text.strip()
                if c_name:
                    countries.add(c_name)

        return sorted(list(countries))

    @staticmethod
    @st.cache_data
    def extract_country_boundaries(gpml_path: str, country_name: str) -> gpd.GeoDataFrame:
        """
        Parses GPML political boundaries file and extracts geometry features for selected country at present-day (age 0).
        Converts coordinates from GPML standard (lat, lon) to Shapely standard (lon, lat).
        """
        if not os.path.exists(gpml_path) or not country_name:
            return gpd.GeoDataFrame()

        tree = ET.parse(gpml_path)
        root = tree.getroot()
        namespaces = {
            "gpml": "http://www.gplates.org/gplates",
            "gml": "http://www.opengis.net/gml",
        }

        geometries = []
        metadata = []

        for feature in root.findall(".//gpml:UnclassifiedFeature", namespaces):
            name_elem = feature.find('.//gpml:key[.="NAME"]/../gpml:value', namespaces)
            name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else ""

            if name.lower() == country_name.lower():
                plate_id = 0
                plate_elem = feature.find(".//gpml:reconstructionPlateId//gpml:value", namespaces)
                if plate_elem is None or not plate_elem.text:
                    plate_elem = feature.find(".//gpml:reconstructionPlateId", namespaces)

                if plate_elem is not None and plate_elem.text:
                    match = re.search(r"\d+", plate_elem.text)
                    if match:
                        try:
                            plate_id = int(match.group())
                        except ValueError:
                            pass

                fips_elem = feature.find('.//gpml:key[.="FIPS_CODE"]/../gpml:value', namespaces)
                fips = fips_elem.text.strip() if (fips_elem is not None and fips_elem.text) else ""

                for pos_list in feature.findall(".//gml:posList", namespaces):
                    raw_coords = list(map(float, pos_list.text.strip().split()))
                    coords = [
                        (raw_coords[i + 1], raw_coords[i]) for i in range(0, len(raw_coords), 2)
                    ]

                    if len(coords) >= 3:
                        if coords[0] == coords[-1] and len(coords) >= 4:
                            geom = Polygon(coords)
                        else:
                            geom = LineString(coords)

                        geometries.append(geom)
                        metadata.append({"name": name, "fips": fips, "plate_id": plate_id})

        return gpd.GeoDataFrame(metadata, geometry=geometries, crs="EPSG:4326")

    def get_country_boundaries(self, country_name: str, target_age: float = 0.0) -> gpd.GeoDataFrame:
        """Retrieves country boundaries and calculates tectonic rotation for requested target age."""
        if not country_name:
            return gpd.GeoDataFrame()

        gpml_path = self._resolve_file("PALEOMAP_PoliticalBoundaries.gpml")
        rot_file = self._resolve_file("PALEOMAP_PlateModel.rot")

        return self.get_reconstructed_country_boundaries(
            gpml_path, rot_file, country_name, float(target_age)
        )

    @staticmethod
    def get_reconstructed_country_boundaries(
        gpml_path: str, rot_file: str, country_name: str, target_age: float
    ) -> gpd.GeoDataFrame:
        """Extracts boundaries and applies Euler rotations via cached lookup or PyGPlates."""
        raw_gdf = ReconstructionService.extract_country_boundaries(gpml_path, country_name)
        if raw_gdf.empty or target_age == 0.0:
            return raw_gdf

        rotations_cache = ReconstructionService.load_plate_rotations_cache()

        # Round target age to nearest 5 Ma step for exact key lookup
        age_step = int(round(target_age / 5.0)) * 5
        reconstructed_geometries = []

        for _, row in raw_gdf.iterrows():
            geom = row.geometry
            plate_id = int(row.get("plate_id", 0))
            cache_key = f"{plate_id}_{age_step}"

            if cache_key in rotations_cache:
                pole_lat, pole_lon, angle_deg = rotations_cache[cache_key]
                new_geom = ReconstructionService.rotate_geometry(geom, pole_lat, pole_lon, angle_deg)
            elif HAS_PYGPLATES and os.path.exists(rot_file):
                try:
                    import pygplates

                    rotation_model = pygplates.RotationModel(rot_file)
                    finite_rotation = rotation_model.get_rotation(
                        float(target_age), moving_plate_id=plate_id, fixed_plate_id=0
                    )
                    pole_lat, pole_lon, angle_deg = finite_rotation.get_lat_lon_euler_pole_and_angle_degrees()
                    new_geom = ReconstructionService.rotate_geometry(geom, pole_lat, pole_lon, angle_deg)
                except Exception:
                    new_geom = geom
            else:
                new_geom = geom

            reconstructed_geometries.append(new_geom)

        rec_gdf = raw_gdf.copy()
        rec_gdf.geometry = reconstructed_geometries
        return rec_gdf