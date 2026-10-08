import os
import re
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
        self.rot_file = os.path.join(self.rotations_dir, "PALEOMAP_PlateModel.rot")
        self.gpml_file = os.path.join(self.rotations_dir, "PALEOMAP_StaticPolygons.gpml")
        self.gpml_boundaries_file = os.path.join(self.reconstructions_dir, "PALEOMAP_PoliticalBoundaries.gpml")

    def _resolve_file(self, filename: str) -> str:
        """Helper to resolve file paths across potential data subdirectories dynamically."""
        candidates = [
            os.path.join(self.reconstructions_dir, filename),
            os.path.join(self.rotations_dir, filename),
            os.path.join("data", "raw", filename),
            os.path.join("data", filename),
        ]
        return next((p for p in candidates if os.path.exists(p)), os.path.join(self.rotations_dir, filename))

    def has_required_files(self) -> bool:
        """Checks if both required PALEOMAP rotation files are present."""
        rot_path = self._resolve_file("PALEOMAP_PlateModel.rot")
        gpml_path = self._resolve_file("PALEOMAP_StaticPolygons.gpml")
        return os.path.exists(rot_path) and os.path.exists(gpml_path)

    def generate_precomputed_npz(
        self, df: pd.DataFrame, lat_col: str, lng_col: str, map_ages: list, output_npz_path: str
    ):
        """Runs PyGPlates reconstruction once across all map ages and saves compressed NPZ archive."""
        rot_file = self._resolve_file("PALEOMAP_PlateModel.rot")
        gpml_file = self._resolve_file("PALEOMAP_StaticPolygons.gpml")

        if not (os.path.exists(rot_file) and os.path.exists(gpml_file)):
            st.warning(
                f"Rotation files missing. Expected PALEOMAP_PlateModel.rot and PALEOMAP_StaticPolygons.gpml."
            )
            return {}

        try:
            import pygplates

            st.info("Generating precomputed coordinates archive using PyGPlates (one-time process)...")

            rotation_model = pygplates.RotationModel(rot_file)
            partition_polygons = pygplates.FeatureCollection(gpml_file)

            lats = df[lat_col].to_numpy()
            lngs = df[lng_col].to_numpy()

            point_features = []
            for lat, lng in zip(lats, lngs):
                pt = pygplates.PointOnSphere(lat, lng)
                feature = pygplates.Feature()
                feature.set_geometry(pt)
                point_features.append(feature)

            partitioned_features = pygplates.partition(point_features, partition_polygons)

            lookup = {}
            for age in map_ages:
                reconstructed_features = []
                pygplates.reconstruct(
                    partitioned_features, rotation_model, reconstructed_features, float(age)
                )

                rec_lats, rec_lngs = [], []
                for rf in reconstructed_features:
                    geom = rf.get_reconstructed_geometry()
                    lat, lng = geom.to_lat_lon()
                    rec_lats.append(lat)
                    rec_lngs.append(lng)

                lookup[f"lng_{age}"] = np.array(rec_lngs, dtype=np.float32)
                lookup[f"lat_{age}"] = np.array(rec_lats, dtype=np.float32)

            os.makedirs(os.path.dirname(output_npz_path), exist_ok=True)
            np.savez_compressed(output_npz_path, **lookup)
            st.success(f"Successfully generated precomputed archive: {output_npz_path}")
            return lookup

        except Exception as e:
            st.error(f"Error during PyGPlates precomputation: {e}")
            return {}

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
        """
        Retrieves country boundaries and calculates tectonic rotation for requested target age.
        """
        if not country_name:
            return gpd.GeoDataFrame()

        gpml_path = self._resolve_file("PALEOMAP_PoliticalBoundaries.gpml")
        rot_file = self._resolve_file("PALEOMAP_PlateModel.rot")

        return self.get_reconstructed_country_boundaries(
            gpml_path, rot_file, country_name, float(target_age)
        )

    @staticmethod
    @st.cache_data
    def get_reconstructed_country_boundaries(
        gpml_path: str, rot_file: str, country_name: str, target_age: float
    ) -> gpd.GeoDataFrame:
        """
        Extracts boundaries and applies tectonic Euler rotations using primitive hashable types for Streamlit caching.
        """
        raw_gdf = ReconstructionService.extract_country_boundaries(gpml_path, country_name)
        if raw_gdf.empty or target_age == 0.0 or not HAS_PYGPLATES or not os.path.exists(rot_file):
            return raw_gdf

        try:
            import pygplates

            rotation_model = pygplates.RotationModel(rot_file)
            reconstructed_geometries = []

            for _, row in raw_gdf.iterrows():
                geom = row.geometry
                plate_id = int(row.get("plate_id", 0))

                finite_rotation = rotation_model.get_rotation(
                    float(target_age), moving_plate_id=plate_id, fixed_plate_id=0
                )

                def rotate_coords(coords_list):
                    rotated = []
                    for lon, lat in coords_list:
                        pt = pygplates.PointOnSphere(lat, lon)
                        rot_pt = finite_rotation * pt
                        r_lat, r_lon = rot_pt.to_lat_lon()
                        rotated.append((r_lon, r_lat))
                    return rotated

                if geom.geom_type == "Polygon":
                    new_exterior = rotate_coords(geom.exterior.coords)
                    new_geom = Polygon(new_exterior)
                elif geom.geom_type == "LineString":
                    new_coords = rotate_coords(geom.coords)
                    new_geom = LineString(new_coords)
                elif geom.geom_type == "MultiPolygon":
                    polys = []
                    for poly in geom.geoms:
                        new_ext = rotate_coords(poly.exterior.coords)
                        polys.append(Polygon(new_ext))
                    new_geom = MultiPolygon(polys)
                else:
                    new_geom = geom

                reconstructed_geometries.append(new_geom)

            rec_gdf = raw_gdf.copy()
            rec_gdf.geometry = reconstructed_geometries
            return rec_gdf

        except Exception:
            return raw_gdf