import numpy as np
import plotly.graph_objects as go

class MapViewBuilder:
    """OOP Builder class for generating Plotly map figures with dynamic clade colors and vector boundaries."""

    COLOR_MAP = {
        'Sauropodes': '#3498db',     # Blue
        'Théropodes': '#e67e22',     # Orange
        'Ornithischiens': '#f1c40f', # Yellow
        'Indéterminé': '#7f8c8d'     # Neutral Grey
    }

    @staticmethod
    def build_figure(df_filtered, active_indices, calc_lngs, calc_lats, b64_image_str, country_gdf=None) -> go.Figure:
        """Builds interactive Plotly figure with styled markers per taxonomic group and red GPML boundary overlay."""
        if len(calc_lngs) > 0:
            rng = np.random.default_rng(seed=42)
            disp_lngs = calc_lngs + rng.uniform(-0.25, 0.25, size=len(calc_lngs))
            disp_lats = calc_lats + rng.uniform(-0.25, 0.25, size=len(calc_lats))
        else:
            disp_lngs, disp_lats = np.array([]), np.array([])

        fig = go.Figure()

        # Render GPML Country Boundaries Overlay in red (#e74c3c)
        if country_gdf is not None and not country_gdf.empty:
            country_label = country_gdf['name'].iloc[0] if 'name' in country_gdf.columns else 'Pays'
            for geom in country_gdf.geometry:
                if geom.geom_type == 'Polygon':
                    x, y = geom.exterior.xy
                    fig.add_trace(go.Scatter(
                        x=list(x),
                        y=list(y),
                        mode='lines',
                        line=dict(color='#e74c3c', width=1.8),
                        name=country_label,
                        hoverinfo='name',
                        showlegend=False
                    ))
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        x, y = poly.exterior.xy
                        fig.add_trace(go.Scatter(
                            x=list(x),
                            y=list(y),
                            mode='lines',
                            line=dict(color='#e74c3c', width=1.8),
                            name=country_label,
                            hoverinfo='name',
                            showlegend=False
                        ))
                elif geom.geom_type == 'LineString':
                    x, y = geom.xy
                    fig.add_trace(go.Scatter(
                        x=list(x),
                        y=list(y),
                        mode='lines',
                        line=dict(color='#e74c3c', width=1.8),
                        name=country_label,
                        hoverinfo='name',
                        showlegend=False
                    ))

        if len(df_filtered) > 0:
            for group_name in df_filtered['dino_group'].unique():
                color = MapViewBuilder.COLOR_MAP.get(group_name, '#7f8c8d')
                mask = (df_filtered['dino_group'] == group_name).to_numpy()

                fig.add_trace(go.Scatter(
                    x=disp_lngs[mask],
                    y=disp_lats[mask],
                    mode='markers',
                    name=group_name,
                    marker=dict(
                        size=11,
                        color=color,
                        line=dict(width=1, color='black'),
                        opacity=0.85
                    ),
                    text=df_filtered.loc[mask, 'hover_label'],
                    hoverinfo='text',
                    customdata=active_indices[mask]
                ))

        fig.update_layout(
            uirevision=True,
            showlegend=False,
            xaxis=dict(
                range=[-180, 180],
                showgrid=False,
                zeroline=False,
                constrain='domain'
            ),
            yaxis=dict(
                range=[-90, 90],
                showgrid=False,
                zeroline=False,
                scaleanchor="x",
                scaleratio=1
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            height=680,
            hovermode='closest',
            clickmode='event+select',
            dragmode='pan',
            paper_bgcolor="#131a24",
            plot_bgcolor="#131a24"
        )

        if b64_image_str:
            fig.add_layout_image(
                dict(
                    source=b64_image_str,
                    xref="x",
                    yref="y",
                    x=-180,
                    y=90,
                    sizex=360,
                    sizey=180,
                    sizing="stretch",
                    opacity=1,
                    layer="below"
                )
            )

        return fig