import os
import numpy as np
import pandas as pd
import streamlit as st

class ReconstructionService:
    """Service dedicated to generating precomputed coordinate NPZ archives using PALEOMAP files."""

    def __init__(self, rotations_dir: str = os.path.join("data", "rotations")):
        self.rotations_dir = rotations_dir
        self.rot_file = os.path.join(self.rotations_dir, "PALEOMAP_PlateModel.rot")
        self.gpml_file = os.path.join(self.rotations_dir, "PALEOMAP_StaticPolygons.gpml")

    def has_required_files(self) -> bool:
        """Checks if both required PALEOMAP rotation files are present."""
        return os.path.exists(self.rot_file) and os.path.exists(self.gpml_file)

    def generate_precomputed_npz(self, df: pd.DataFrame, lat_col: str, lng_col: str, map_ages: list, output_npz_path: str):
        """Runs PyGPlates reconstruction once across all map ages and saves compressed NPZ archive."""
        if not self.has_required_files():
            st.warning(f"Rotation files missing in {self.rotations_dir}. Expected PALEOMAP_PlateModel.rot and PALEOMAP_StaticPolygons.gpml.")
            return {}

        try:
            import pygplates
            st.info("Generating precomputed coordinates archive using PyGPlates (one-time process)...")

            rotation_model = pygplates.RotationModel(self.rot_file)
            partition_polygons = pygplates.FeatureCollection(self.gpml_file)

            lats = df[lat_col].to_numpy()
            lngs = df[lng_col].to_numpy()

            # Create base point features
            point_features = []
            for lat, lng in zip(lats, lngs):
                pt = pygplates.PointOnSphere(lat, lng)
                feature = pygplates.Feature()
                feature.set_geometry(pt)
                point_features.append(feature)

            # Assign plate IDs
            partitioned_features = pygplates.partition(point_features, partition_polygons)

            lookup = {}
            for age in map_ages:
                reconstructed_features = []
                pygplates.reconstruct(partitioned_features, rotation_model, reconstructed_features, float(age))

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