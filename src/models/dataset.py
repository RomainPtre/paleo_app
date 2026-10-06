import pandas as pd
import numpy as np

class DinosaurDataset:
    """Encapsulates PBDB dinosaur occurrence data and temporal filtering logic."""

    def __init__(self, df: pd.DataFrame, lat_col: str, lng_col: str, precomputed_lookup: dict):
        self.df = df
        self.lat_col = lat_col
        self.lng_col = lng_col
        self.precomputed_lookup = precomputed_lookup

    def get_filtered_occurrences(self, target_age: float, window: float = 2.5):
        """Filters dataset rows matching the target age window."""
        mask = (self.df['min_ma'] <= (target_age + window)) & (self.df['max_ma'] >= (target_age - window))
        df_filtered = self.df[mask].copy()
        indices = df_filtered.index.values
        return df_filtered, indices

    def get_coordinates(self, indices: np.ndarray, paleodem_age: int):
        """Retrieves recalculated paleogeographic or present-day coordinates."""
        if self.precomputed_lookup and paleodem_age is not None and f"lng_{paleodem_age}" in self.precomputed_lookup and len(indices) > 0:
            calc_lngs = self.precomputed_lookup[f"lng_{paleodem_age}"][indices]
            calc_lats = self.precomputed_lookup[f"lat_{paleodem_age}"][indices]
        elif len(indices) > 0:
            df_sub = self.df.loc[indices]
            calc_lngs = df_sub[self.lng_col].to_numpy()
            calc_lats = df_sub[self.lat_col].to_numpy()
        else:
            calc_lngs, calc_lats = np.array([]), np.array([])
            
        return calc_lngs, calc_lats