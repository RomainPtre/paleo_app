import streamlit as st

class SidebarView:
    """Composant d'affichage pour la barre latérale Streamlit."""

    @staticmethod
    def render_info(occurrences_count: int):
        st.sidebar.header("📊 Informations")
        st.sidebar.metric("Occurrences affichées", occurrences_count)

    @staticmethod
    def render_selected_specimen(df_pbdb, customdata_idx, container=None):
        target = container if container is not None else st.sidebar
        if customdata_idx is not None and customdata_idx in df_pbdb.index:
            dino = df_pbdb.loc[customdata_idx]
            target.markdown("---")
            target.subheader("📌 Spécimen sélectionné")
            target.markdown(f"### *{dino.get('accepted_name', dino.get('identified_name', 'Inconnu'))}*")
            target.write(f"**Groupe :** `{dino.get('dino_group')}`")
            target.write(f"**Famille :** {dino.get('family', 'N/A')}")

            expander = target.expander("Toutes les métadonnées PBDB")
            expander.json(dino.to_dict())