import os
import pandas as pd
import numpy as np
import streamlit as st
from src.models.dataset import DinosaurDataset
from src.services.reconstruction_service import ReconstructionService
from src.services.map_service import MapService

class PreprocessorService:
    """Service handling dataset initialization, CSV parsing, and clade classification."""

    @staticmethod
    @st.cache_data
    def load_and_preprocess() -> DinosaurDataset:
        raw_csv_path = os.path.join("data", "raw", "pbdb_dinosaurs.csv")
        npz_path = os.path.join("data", "processed", "precomputed_coords.npz")

        if not os.path.exists(raw_csv_path):
            raw_csv_path = os.path.join("data", "pbdb_dinosaurs.csv")

        if not os.path.exists(raw_csv_path):
            st.error(f"CSV file not found: {raw_csv_path}")
            st.stop()

        df = pd.read_csv(raw_csv_path, low_memory=False)
        lat_col = next((c for c in ['lat', 'decimallatitude', 'latitude'] if c in df.columns), 'lat')
        lng_col = next((c for c in ['lng', 'decimallongitude', 'longitude'] if c in df.columns), 'lng')
        df = df.dropna(subset=[lat_col, lng_col]).reset_index(drop=True)

        # Keyword tuples for systematic clade matching across PBDB taxonomy fields (alphabetically sorted)
        theropod_keywords = (
            'abelisaur', 'allosaur', 'aves', 'averostr', 'avetheropod',
            'caegnathid', 'carcharodontosaur', 'ceratosaur', 'coelurosaur',
            'dromaeosaur', 'maniraptor', 'megalosaur', 'neothero', 'noasaur',
            'orionid', 'ornithomimid', 'ornithomimo', 'oviraptor',
            'oviraptosaur', 'pennaraptor', 'spinosaur', 'tetanur',
            'therizinosaur', 'theropod', 'theropoda', 'troodontid',
            'tyrannosaur'
        )

        sauropod_keywords = (
            'brachiosaur', 'camarasaur', 'cetiosaur', 'dicraeosaur',
            'diplodoc', 'eusauropod', 'flagellicaud', 'lithostro',
            'macronaria', 'mamenchisaur', 'neosauropod', 'rebbachisaur',
            'sauropod', 'sauropodomorpha', 'somphospond', 'titanosaur',
            'turiasaur'
        )

        ornithischian_keywords = (
            'ankylosaur', 'ceratops', 'fabrosaur', 'hadrosaur',
            'heterodontosaur', 'hypsilophodont', 'iguanodont',
            'ornithisch', 'pachycephalosaur', 'scelidosaur', 'stegosaur'
        )

        # Assign explicit French frontend display labels for dinosaur clades
        def assign_dino_group(r):
            text = f"{r.get('order','')} {r.get('class','')} {r.get('family','')} {r.get('accepted_name','')} {r.get('identified_name','')}".lower()
            if any(keyword in text for keyword in theropod_keywords):
                return 'Théropodes'
            elif any(keyword in text for keyword in sauropod_keywords):
                return 'Sauropodes'
            elif any(keyword in text for keyword in ornithischian_keywords):
                return 'Ornithischiens'
            return 'Indéterminé'

        df['dino_group'] = df.apply(assign_dino_group, axis=1)
        df['hover_label'] = df.apply(
            lambda r: f"<b><i>{r.get('accepted_name', r.get('identified_name', 'Indéterminé'))}</i></b><br>"
                      f"Groupe : <b>{r.get('dino_group')}</b><br>"
                      f"Âge : {r.get('max_ma', '?')} - {r.get('min_ma', '?')} Ma", axis=1
        )

        lookup = {}
        if os.path.exists(npz_path):
            with np.load(npz_path) as data:
                lookup = {k: data[k] for k in data.files}
        else:
            dem_store, _ = MapService.load_all_paleodems()
            map_ages = list(dem_store.keys()) if dem_store else []
            reconstruction_service = ReconstructionService()
            if reconstruction_service.has_required_files() and map_ages:
                lookup = reconstruction_service.generate_precomputed_npz(df, lat_col, lng_col, map_ages, npz_path)

        return DinosaurDataset(df, lat_col, lng_col, lookup)