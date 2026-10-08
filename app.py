import os
import streamlit as st
from src.services.preprocessor import PreprocessorService
from src.services.map_service import MapService
from src.services.timeline_service import TimelineService
from src.services.silhouette_service import SilhouetteService
from src.services.search_service import SearchService
from src.services.reconstruction_service import ReconstructionService
from src.ui.map_view import MapViewBuilder
from src.ui.sidebar_view import SidebarView

# -----------------------------------------------------------------------------
# Streamlit Application Setup & Dynamic Button CSS
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Le monde des dinosaures", page_icon="🦖")

# Initialize session state variables
for group_key in ["show_sauro", "show_thero", "show_ornitho", "show_indet"]:
    if group_key not in st.session_state:
        st.session_state[group_key] = True

if "target_age" not in st.session_state:
    st.session_state.target_age = 0

if "show_country_boundary" not in st.session_state:
    st.session_state.show_country_boundary = False

def toggle_group(key_name: str):
    """Callback function toggling single clade visibility in session state."""
    st.session_state[key_name] = not st.session_state[key_name]

def toggle_all(target_state: bool):
    """Callback function toggling all clades to requested target boolean state."""
    for group_key in ["show_sauro", "show_thero", "show_ornitho", "show_indet"]:
        st.session_state[group_key] = target_state

# Master toggle state computation
all_active = all(st.session_state[k] for k in ["show_sauro", "show_thero", "show_ornitho", "show_indet"])
master_label = "Tout cacher" if all_active else "Tout afficher"
master_bg = "#e74c3c" if all_active else "#2ecc71"
master_txt = "#ffffff"

sauro_bg = "#3498db" if st.session_state.show_sauro else "#1e293b"
sauro_txt = "#ffffff" if st.session_state.show_sauro else "#64748b"

thero_bg = "#e67e22" if st.session_state.show_thero else "#1e293b"
thero_txt = "#ffffff" if st.session_state.show_thero else "#64748b"

ornitho_bg = "#f1c40f" if st.session_state.show_ornitho else "#1e293b"
ornitho_txt = "#000000" if st.session_state.show_ornitho else "#64748b"

indet_bg = "#7f8c8d" if st.session_state.show_indet else "#1e293b"
indet_txt = "#ffffff" if st.session_state.show_indet else "#64748b"

st.markdown(f"""
<style>
div[data-testid="stPlotlyChart"], 
div[data-testid="stPlotlyChart"] * {{
 transition: none !important;
 opacity: 1 !important;
}}
div[data-testid="stElementContainer"] {{
 transition: none !important;
}}

.st-key-btn_master button, .st-key-btn_master button:hover, .st-key-btn_master button:focus {{
 background-color: {master_bg} !important;
 color: {master_txt} !important;
 border: 1px solid {master_bg} !important;
 font-weight: bold !important;
 width: 100% !important;
}}
.st-key-btn_master button p {{
 color: {master_txt} !important;
}}

.st-key-btn_sauro button, .st-key-btn_sauro button:hover, .st-key-btn_sauro button:focus {{
 background-color: {sauro_bg} !important;
 color: {sauro_txt} !important;
 border: 1px solid {sauro_bg} !important;
 font-weight: bold !important;
 width: 100% !important;
}}
.st-key-btn_sauro button p {{
 color: {sauro_txt} !important;
}}

.st-key-btn_thero button, .st-key-btn_thero button:hover, .st-key-btn_thero button:focus {{
 background-color: {thero_bg} !important;
 color: {thero_txt} !important;
 border: 1px solid {thero_bg} !important;
 font-weight: bold !important;
 width: 100% !important;
}}
.st-key-btn_thero button p {{
 color: {thero_txt} !important;
}}

.st-key-btn_ornitho button, .st-key-btn_ornitho button:hover, .st-key-btn_ornitho button:focus {{
 background-color: {ornitho_bg} !important;
 color: {ornitho_txt} !important;
 border: 1px solid {ornitho_bg} !important;
 font-weight: bold !important;
 width: 100% !important;
}}
.st-key-btn_ornitho button p {{
 color: {ornitho_txt} !important;
}}

.st-key-btn_indet button, .st-key-btn_indet button:hover, .st-key-btn_indet button:focus {{
 background-color: {indet_bg} !important;
 color: {indet_txt} !important;
 border: 1px solid {indet_bg} !important;
 font-weight: bold !important;
 width: 100% !important;
}}
.st-key-btn_indet button p {{
 color: {indet_txt} !important;
}}

/* Typography adjustments for slider age value label */
div[data-testid="stSlider"] p {{
 font-size: 1.15rem !important;
 font-weight: bold !important;
}}
</style>
""", unsafe_allow_html=True)

# 1. Initialize core services
dataset = PreprocessorService.load_and_preprocess()
dem_store, dem_file_map = MapService.load_all_paleodems()
timeline_service = TimelineService()
base_chart_img = timeline_service.load_base_chart()

reconstruction_service = ReconstructionService()

# --- 1. App Title ---
st.title("🦖 Le monde des dinosaures")

# --- 2. Header layout: Search bar on left, Clade filters on right ---
col_search, col_filters = st.columns([1, 1.2])

search_specimen_idx = None
selected_dino = None

with col_search:
    with st.container(border=True):
        st.markdown("**🔍 Rechercher un dinosaure**")
        search_options = SearchService.get_unique_names(dataset.df)
        
        selected_dino = st.selectbox(
            "Recherche par nom accepted_name",
            options=search_options,
            index=None,
            placeholder="Tapez un nom (ex: Tyrannosaurus)...",
            key="dino_search_select",
            label_visibility="collapsed"
        )
        
        if selected_dino:
            spec_idx, spec_age = SearchService.get_specimen_search_details(dataset.df, selected_dino)
            search_specimen_idx = spec_idx
            if spec_age is not None and st.session_state.get("last_searched_dino") != selected_dino:
                st.session_state.target_age = spec_age
                st.session_state.last_searched_dino = selected_dino

with col_filters:
    with st.container(border=True):
        h_col1, h_col2 = st.columns([1.5, 1])
        with h_col1:
            st.markdown("**Filtre à dinosaures**")
        with h_col2:
            st.button(master_label, key="btn_master", on_click=toggle_all, args=(not all_active,))

        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            sc1, sc2 = st.columns([1, 2.5], vertical_alignment="center")
            with sc1:
                img_sauro = SilhouetteService.get_colored_silhouette(
                    "data/assets/silhouettes/Patagotitan.png", MapViewBuilder.COLOR_MAP['Sauropodes']
                )
                st.image(img_sauro, width="stretch")
            with sc2:
                st.button("Sauropodes", key="btn_sauro", on_click=toggle_group, args=("show_sauro",))

        with c2:
            sc1, sc2 = st.columns([1, 2.5], vertical_alignment="center")
            with sc1:
                img_thero = SilhouetteService.get_colored_silhouette(
                    "data/assets/silhouettes/Tyrannosaurus_sil.png", MapViewBuilder.COLOR_MAP['Théropodes']
                )
                st.image(img_thero, width="stretch")
            with sc2:
                st.button("Théropodes", key="btn_thero", on_click=toggle_group, args=("show_thero",))

        with c3:
            sc1, sc2 = st.columns([1, 2.5], vertical_alignment="center")
            with sc1:
                img_stego = SilhouetteService.get_colored_silhouette(
                    "data/assets/silhouettes/Stego.png", MapViewBuilder.COLOR_MAP['Ornithischiens']
                )
                st.image(img_stego, width="stretch")
            with sc2:
                st.button("Ornithischiens", key="btn_ornitho", on_click=toggle_group, args=("show_ornitho",))

        with c4:
            st.button("Indéterminé", key="btn_indet", on_click=toggle_group, args=("show_indet",))

# --- 3. Country Search Container ---
with st.container(border=True):
    st.markdown("**🔍 Rechercher un pays**")
    col_p1, col_p2 = st.columns([2.5, 1], vertical_alignment="bottom")
    
    country_options = reconstruction_service.get_available_countries()
    
    with col_p1:
        selected_country = st.selectbox(
            "Rechercher un pays",
            options=country_options,
            index=None,
            placeholder="Tapez un nom de pays (ex: France, USA)...",
            key="country_search_select",
            label_visibility="collapsed"
        )
        
        if selected_country and st.session_state.get("last_selected_country") != selected_country:
            st.session_state.show_country_boundary = True
            st.session_state.last_selected_country = selected_country
        elif not selected_country:
            st.session_state.last_selected_country = None

    with col_p2:
        show_country_boundary = st.checkbox(
            "Afficher le contour",
            key="show_country_boundary"
        )

# --- 4. Target Age Slider Container ---
with st.container(border=True):
    st.markdown("**⏱️ Âge de la carte (Millions d'années)**")
    target_age = st.slider(
        "⏱️ Âge de la carte (Millions d'années)",
        min_value=0,
        max_value=320,
        step=5,
        key="target_age",
        label_visibility="collapsed"
    )

# 5. Process paleodem raster and filtered fossil occurrences
b64_image_str, paleodem_filename, paleodem_age = MapService.get_closest_map(dem_store, dem_file_map, target_age)

country_reconstructed_gdf = (
    reconstruction_service.get_country_boundaries(country_name=selected_country, target_age=paleodem_age)
    if (show_country_boundary and selected_country) else None
)

df_filtered, active_indices = dataset.get_filtered_occurrences(target_age)

if selected_dino and not df_filtered.empty and "accepted_name" in df_filtered.columns:
    mask_search = (df_filtered["accepted_name"] == selected_dino).to_numpy()
    df_filtered = df_filtered[mask_search]
    active_indices = active_indices[mask_search]

calc_lngs, calc_lats = dataset.get_coordinates(active_indices, paleodem_age)

selected_groups = []
if st.session_state.show_sauro:
    selected_groups.append('Sauropodes')
if st.session_state.show_thero:
    selected_groups.append('Théropodes')
if st.session_state.show_ornitho:
    selected_groups.append('Ornithischiens')
if st.session_state.show_indet:
    selected_groups.append('Indéterminé')

if len(df_filtered) > 0:
    mask_groups = df_filtered['dino_group'].isin(selected_groups).to_numpy()
    df_filtered = df_filtered[mask_groups]
    active_indices = active_indices[mask_groups]
    calc_lngs = calc_lngs[mask_groups]
    calc_lats = calc_lats[mask_groups]

# 6. Render sidebar components
SidebarView.render_info(len(df_filtered))
specimen_container = st.sidebar.container()

st.sidebar.markdown("---")
st.sidebar.subheader("⏳ Échelle des temps")
if base_chart_img is not None:
    chart_with_indicator = timeline_service.render_chart_with_cursor(base_chart_img, target_age)
    st.sidebar.image(chart_with_indicator, width="stretch")
else:
    st.sidebar.warning("Charte introuvable dans data/assets/illustrations/")

# 7. Build interactive Plotly map with reconstructed country boundary overlay
fig = MapViewBuilder.build_figure(
    df_filtered, active_indices, calc_lngs, calc_lats, b64_image_str, country_gdf=country_reconstructed_gdf
)

selection = st.plotly_chart(
    fig,
    width="stretch",
    on_select="rerun",
    selection_mode=("points", "box"),
    key="map_canvas"
)

# 8. Render selected specimen details in reserved sidebar container
selected_customdata_idx = None

if selection and isinstance(selection, dict) and "selection" in selection:
    pts = selection["selection"].get("points", [])
    if pts:
        point_data = pts[0]
        selected_customdata_idx = point_data.get("customdata")

final_specimen_idx = search_specimen_idx if search_specimen_idx is not None else selected_customdata_idx

if final_specimen_idx is not None:
    SidebarView.render_selected_specimen(dataset.df, final_specimen_idx, container=specimen_container)

# --- 9. References and Acknowledgments Container ---
st.markdown("---")
with st.container(border=True):
    col_logo, col_credits = st.columns([1, 4], vertical_alignment="center")

    logo_path = os.path.join("assets", "logo", "Logo-DIM_PAMIR-FINAL_RVB-accroche_regionIDF.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join("data", "assets", "logo", "Logo-DIM_PAMIR-FINAL_RVB-accroche_regionIDF.png")

    with col_logo:
        if os.path.exists(logo_path):
            st.image(logo_path, use_container_width=True)

    with col_credits:
        st.markdown("""
<p style="font-style: italic;">
  <u><b>Références et remerciements</b></u>
</p>

- *Reconstructions paléogéographiques : Scotese, C. R., & Wright, N. (2018). PALEOMAP paleodigital elevation models (PaleoDEMS) for the Phanerozoic. Paleomap Proj, 1, 26.*
- *La base de données de dinosaures non-aviens provient de la <a href="https://paleobiodb.org/classic" target="_blank">PBDB</a> (accès le 5/10/2026).*
- *Échelle chronostratigraphique : Karlstrom, K. E. (2021). Telling time at Grand Canyon National Park: 2020 update. US Department of the Interior, National Park Service, Natural Resource Stewardship and Science. Modifiée à partir de Cohen, K. M., Finney, S. C., Gibbard, P. L., & Fan, J. X. (2013). The ICS international chronostratigraphic chart. Episodes Journal of International Geoscience, 36(3), 199-204.*
- *Silhouettes de dinosaures : S. Hartman*
- *Financements : DIM PAMIR dans le cadre du projet EcoCLimat (R. Pintore et al.)*
""", unsafe_allow_html=True)