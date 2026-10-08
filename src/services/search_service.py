import pandas as pd


class SearchService:
    """Service OOP pour la recherche textuelle et le filtrage des dinosaures par accepted_name."""

    @staticmethod
    def get_unique_names(df: pd.DataFrame) -> list[str]:
        """Extrait la liste triée et unique des noms acceptés (accepted_name)."""
        if df is None or df.empty or "accepted_name" not in df.columns:
            return []
        return sorted(df["accepted_name"].dropna().unique().tolist())

    @staticmethod
    def get_specimen_search_details(
        df: pd.DataFrame, selected_name: str, map_ages: list[int] | None = None
    ) -> tuple[int | None, int | None, tuple[float | None, float | None]]:
        """
        Retourne l'index du spécimen (customdata), l'âge de la carte (pas de 5 Ma) comportant le plus grand
        nombre d'occurrences pour le taxon sélectionné, ainsi que sa plage temporelle globale (max_ma, min_ma).
        """
        if df is None or df.empty or not selected_name or "accepted_name" not in df.columns:
            return None, None, (None, None)

        matches = df[df["accepted_name"] == selected_name]
        if matches.empty:
            return None, None, (None, None)

        first_match = matches.iloc[0]
        specimen_idx = first_match.name

        # Extrait la plage temporelle globale du taxon (de l'âge max à l'âge min)
        max_ma = matches["max_ma"].max() if "max_ma" in matches.columns and pd.notna(matches["max_ma"].max()) else None
        min_ma = matches["min_ma"].min() if "min_ma" in matches.columns and pd.notna(matches["min_ma"].min()) else None

        if map_ages is None:
            map_ages = list(range(0, 325, 5))

        # Détermine le pas de carte ayant le plus grand nombre d'occurrences
        best_age = map_ages[0]
        max_count = -1

        for age in map_ages:
            if "min_ma" in matches.columns and "max_ma" in matches.columns:
                count = ((matches["min_ma"] <= age) & (matches["max_ma"] >= age)).sum()
            else:
                count = 0

            if count > max_count:
                max_count = count
                best_age = age

        return specimen_idx, best_age, (max_ma, min_ma)