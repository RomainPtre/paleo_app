from PIL import Image
import streamlit as st


class SilhouetteService:
    """Service OOP pour le chargement, la recoloration et la mise en cache des silhouettes de dinosaures."""

    @staticmethod
    @st.cache_data
    def get_colored_silhouette(image_path: str, hex_color: str) -> Image.Image:
        """Charge un fichier PNG transparent et applique la couleur Hex sur la couche Alpha."""
        img = Image.open(image_path).convert("RGBA")
        clean_hex = hex_color.lstrip("#")
        rgb = tuple(int(clean_hex[i : i + 2], 16) for i in (0, 2, 4))

        alpha = img.getchannel("A")
        colored_img = Image.new("RGBA", img.size, rgb + (255,))
        colored_img.putalpha(alpha)
        return colored_img