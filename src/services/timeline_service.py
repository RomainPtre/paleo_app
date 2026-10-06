import os
import glob
import streamlit as st
from PIL import Image, ImageDraw
from src.models.timeline import GeologicTimelineModel

class TimelineService:
    """Service d'affichage de l'échelle géologique et du curseur temporel."""

    def __init__(self):
        self.model = GeologicTimelineModel()

    @staticmethod
    @st.cache_data
    def load_base_chart():
        possible_paths = [
            os.path.join("data", "assets", "illustrations", "chronostratigraphic_chart_cohenetal_2013.png"),
            os.path.join("data", "illustrations", "chronostratigraphic_chart_cohenetal_2013.png")
        ]

        img_path = next((p for p in possible_paths if os.path.exists(p)), None)

        if not img_path:
            for parent_dir in [os.path.join("data", "assets", "illustrations"), os.path.join("data", "illustrations")]:
                if os.path.exists(parent_dir):
                    files = glob.glob(os.path.join(parent_dir, "*. [pP][nN][gG]"))
                    if files:
                        img_path = files[0]
                        break

        if not img_path or not os.path.exists(img_path):
            return None

        return Image.open(img_path).convert("RGB")

    def render_chart_with_cursor(self, base_img: Image.Image, age: float) -> Image.Image:
        """Trace la ligne rouge et une flèche de repère pointant vers la droite vers l'échelle des âges."""
        if base_img is None:
            return None

        y_pos = self.model.get_y_position(age)
        chart_draw = base_img.copy()
        draw = ImageDraw.Draw(chart_draw)

        # Ligne horizontale rouge traversant l'image
        y0 = max(0, y_pos - 2)
        y1 = min(chart_draw.height, y_pos + 2)
        draw.rectangle([0, y0, chart_draw.width, y1], fill=(231, 76, 60), outline=(0, 0, 0), width=1)

        # Flèche rouge (►) sur le bord gauche pointant vers la droite
        arrow_size = 12
        arrow_points = [
            (0, y_pos - arrow_size),
            (0, y_pos + arrow_size),
            (arrow_size + 6, y_pos)
        ]
        draw.polygon(arrow_points, fill=(231, 76, 60), outline=(0, 0, 0))

        return chart_draw