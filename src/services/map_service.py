import os
import glob
import re
import base64
import streamlit as st

class MapService:
    """Service indexing and converting paleogeographic DEM rasters to Base64 strings."""

    @staticmethod
    @st.cache_resource
    def load_all_paleodems():
        possible_dirs = [
            os.path.join("data", "maps", "paleodems"),
            os.path.join("data", "paleodems")
        ]
        
        paleodem_dir = next((d for d in possible_dirs if os.path.exists(d)), possible_dirs[0])
        files = glob.glob(os.path.join(paleodem_dir, "*.[jJ][pP][gG]")) + \
                glob.glob(os.path.join(paleodem_dir, "*.[jJ][pP][eE][gG]")) + \
                glob.glob(os.path.join(paleodem_dir, "*.[pP][nN][gG]"))

        dem_store = {}
        file_map = {}

        for f in files:
            numbers = re.findall(r'\d+', os.path.basename(f))
            if numbers:
                age = int(numbers[-1])
                ext = os.path.splitext(f)[1].lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"

                with open(f, "rb") as img_f:
                    b64_encoded = base64.b64encode(img_f.read()).decode("utf-8")
                    dem_store[age] = f"data:{mime_type};base64,{b64_encoded}"
                    file_map[age] = os.path.basename(f)

        return dem_store, file_map

    @classmethod
    def get_closest_map(cls, dem_store: dict, dem_file_map: dict, target_age: float):
        """Returns closest pre-loaded Base64 map image for requested geological age."""
        if not dem_store:
            return None, None, None
        best_age = min(dem_store.keys(), key=lambda a: abs(a - target_age))
        return dem_store[best_age], dem_file_map.get(best_age, ""), best_age