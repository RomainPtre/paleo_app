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
    def get_specimen_search_details(df: pd.DataFrame, selected_name: str) -> tuple[int | None, int | None]:
        """
        Retourne l'index du spécimen (customdata) et son âge géologique arrondi au pas de 5 Ma
        pour le taxon sélectionné.
        """
        if df is None or df.empty or not selected_name or "accepted_name" not in df.columns:
            return None, None

        matches = df[df["accepted_name"] == selected_name]
        if matches.empty:
            return None, None

        first_match = matches.iloc[0]
        specimen_idx = first_match.name

        # Détermination de l'âge géologique moyen du taxon
        raw_age = None
        if "mean_ma" in matches.columns and pd.notna(matches["mean_ma"].mean()):
            raw_age = matches["mean_ma"].mean()
        elif "max_ma" in matches.columns and "min_ma" in matches.columns:
            valid_m = matches.dropna(subset=["max_ma", "min_ma"])
            if not valid_m.empty:
                raw_age = ((valid_m["max_ma"] + valid_m["min_ma"]) / 2).mean()

        if raw_age is None:
            for col in ["mean_ma", "max_ma", "age", "min_ma"]:
                if col in first_match and pd.notna(first_match[col]):
                    raw_age = float(first_match[col])
                    break

        if raw_age is None:
            return specimen_idx, None

        # Arrondi au pas de 5 Ma (ex: 66 Ma -> 65 Ma, 68 Ma -> 70 Ma)
        specimen_age = int(round(raw_age / 5.0) * 5)
        specimen_age = max(0, min(320, specimen_age))

        return specimen_idx, specimen_age