import streamlit as st
from src.services.preprocessor import PreprocessorService
from src.services.map_service import MapService
from src.services.timeline_service import TimelineService
from src.ui.map_view import MapViewBuilder
from src.ui.sidebar_view import SidebarView

# -----------------------------------------------------------------------------
# Streamlit Application Setup & Dynamic Button CSS
# -----------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Le monde des dinosaures", page_icon="🦖")

# Initialize session state variables for group filters
for group_key in ["show_sauro", "show_thero", "show_ornitho", "show_indet"]:
    if group_key not in st.session_state:
        st.session_state[group_key] = True

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

# Define dynamic background colors based on active/inactive toggle state
sauro_bg = "#3498db" if st.session_state.show_sauro else "#1e293b"
sauro_txt = "#ffffff" if st.session_state.show_sauro else "#64748b"

thero_bg = "#e67e22" if st.session_state.show_thero else "#1e293b"  # Updated to Orange
thero_txt = "#ffffff" if st.session_state.show_thero else "#64748b"

ornitho_bg = "#f1c40f" if st.session_state.show_ornitho else "#1e293b"
ornitho_txt = "#000000" if st.session_state.show_ornitho else "#64748b"

indet_bg = "#7f8c8d" if st.session_state.show_indet else "#1e293b"
indet_txt = "#ffffff" if st.session_state.show_indet else "#64748b"

st.markdown(f"""
<style>
/* Anti-flicker styling for Plotly container */
div[data-testid="stPlotlyChart"], 
div[data-testid="stPlotlyChart"] * {{
    transition: none !important;
    opacity: 1 !important;
}}
div[data-testid="stElementContainer"] {{
    transition: none !important;
}}

/* Dynamic styling for master toggle button */
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

/* Custom styled filter buttons targeting button tag and paragraph child */
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
</style>
""", unsafe_allow_html=True)

# 1. Initialize core services
dataset = PreprocessorService.load_and_preprocess()
dem_store, dem_file_map = MapService.load_all_paleodems()
timeline_service = TimelineService()
base_chart_img = timeline_service.load_base_chart()

# 2. Header layout: Title on left, Filter buttons frame on right
col_title, col_filters = st.columns([1, 1.2])

with col_title:
    st.title("🦖 Le monde des dinosaures")

with col_filters:
    with st.container(border=True):
        h_col1, h_col2 = st.columns([1.5, 1])
        with h_col1:
            st.markdown("**Filtre à dinosaures**")
        with h_col2:
            st.button(master_label, key="btn_master", on_click=toggle_all, args=(not all_active,))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.button("Sauropodes", key="btn_sauro", on_click=toggle_group, args=("show_sauro",))
        with c2:
            st.button("Théropodes", key="btn_thero", on_click=toggle_group, args=("show_thero",))
        with c3:
            st.button("Ornithischiens", key="btn_ornitho", on_click=toggle_group, args=("show_ornitho",))
        with c4:
            st.button("Indéterminé", key="btn_indet", on_click=toggle_group, args=("show_indet",))

# 3. Main time navigation slider
target_age = st.slider("⏱️ Âge de la carte (Ma)", min_value=0, max_value=320, value=100, step=5)

# 4. Process paleodem and filtered occurrences
b64_image_str, paleodem_filename, paleodem_age = MapService.get_closest_map(dem_store, dem_file_map, target_age)
df_filtered, active_indices = dataset.get_filtered_occurrences(target_age)
calc_lngs, calc_lats = dataset.get_coordinates(active_indices, paleodem_age)

# Build active clade list from session state toggle buttons
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

# 5. Render sidebar components
SidebarView.render_info(len(df_filtered))
specimen_container = st.sidebar.container()

st.sidebar.markdown("---")
st.sidebar.subheader("⏳ Échelle des temps")
if base_chart_img is not None:
    chart_with_indicator = timeline_service.render_chart_with_cursor(base_chart_img, target_age)
    st.sidebar.image(chart_with_indicator, use_container_width=True)
else:
    st.sidebar.warning("Charte introuvable dans data/assets/illustrations/")

# 6. Build interactive map
fig = MapViewBuilder.build_figure(
    df_filtered, active_indices, calc_lngs, calc_lats, b64_image_str
)

selection = st.plotly_chart(
    fig,
    width="stretch",
    on_select="rerun",
    selection_mode=("points", "box"),
    key="map_canvas"
)

# 7. Render selected specimen details in reserved container
if selection and isinstance(selection, dict) and "selection" in selection:
    pts = selection["selection"].get("points", [])
    if pts:
        point_data = pts[0]
        customdata_idx = point_data.get("customdata")
        SidebarView.render_selected_specimen(dataset.df, customdata_idx, container=specimen_container)