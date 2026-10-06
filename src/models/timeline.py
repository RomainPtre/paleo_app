import numpy as np

class GeologicTimelineModel:
    """Modèle de calibration mathématique pour la Charte Chronostratigraphique Internationale (Cohen et al. 2013)."""

    # Nœuds de calibration (Âge en Ma, Coordonnée Y en pixels sur l'image 1694 px)
    # Période 66 - 240 Ma CONSERVÉE INTACTE.
    # Recalibrage du Cénozoïque (< 66 Ma) et du Paléozoïque (> 240 Ma) d'après les relevés d'erreur.
    CHRONO_KNOTS = [
        (0.0, 20.0),       # Sommet Holocène / Présent
        (0.0117, 43.0),    # Limite Holocène / Pléistocène
        (2.58, 95.0),      # Limite Pléistocène / Pliocène
        (5.333, 164.0),    # Limite Pliocène / Miocène
        (23.03, 220.0),    # Base Néogène (23.03 Ma)
        (33.9, 248.0),     # Limite Oligocène / Éocène — Recalibré
        (56.0, 309.0),     # Limite Éocène / Paléocène — Recalibré
        (66.0, 336.0),     # Limite Paléocène / Crétacé (K-Pg) — NON TOUCHÉ (Secteur 66-240 Ma)
        (100.5, 370.0),    # Crétacé sup. / inf. — NON TOUCHÉ (Secteur 66-240 Ma)
        (145.0, 430.0),    # Limite Crétacé / Jurassique (J-K) — NON TOUCHÉ (Secteur 66-240 Ma)
        (201.3, 539.0),    # Limite Jurassique / Trias (Tr-J) — NON TOUCHÉ (Secteur 66-240 Ma)
        (251.902, 630.0),  # Limite Trias / Permien (P-Tr) — Recalibré
        (298.9, 748.0),    # Limite Permien / Carbonifère — Recalibré
        (323.2, 837.0),    # Limite Pennsylvanien / Mississippien — Recalibré
        (358.9, 914.0),    # Limite Carbonifère / Dévonien — Recalibré
        (419.2, 1040.0),   # Limite Dévonien / Silurien
        (443.8, 1076.0),   # Limite Silurien / Ordovicien
        (485.4, 1127.0),   # Limite Ordovicien / Cambrien
        (541.0, 1294.0),   # Limite Cambrien / Précambrien
        (1000.0, 1379.0),  # Néoprotérozoïque / Mésoprotérozoïque
        (1600.0, 1394.0),  # Mésoprotérozoïque / Paléoprotérozoïque
        (2500.0, 1468.0),  # Paléoprotérozoïque / Archéen
        (4000.0, 1560.0),  # Archéen / Hadéen
        (4600.0, 1677.0)   # Base Hadéen
    ]

    def __init__(self):
        self.known_ages = [k[0] for k in self.CHRONO_KNOTS]
        self.known_ys = [k[1] for k in self.CHRONO_KNOTS]

    def get_y_position(self, age: float) -> int:
        """Calcule la coordonnée Y en pixels par interpolation linéaire par morceaux."""
        return int(np.interp(age, self.known_ages, self.known_ys))