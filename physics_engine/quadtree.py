"""
quadtree.py
===========
Structure de données Quadtree pour accélérer la détection de collisions.

Principe :
  - On découpe l'espace en 4 quadrants récursivement.
  - Une balle n'est testée que contre les balles du même quadrant (ou voisins).
  - Complexité : O(n log n) au lieu de O(n²).

            |
   NW (0)   |   NE (1)
            |
  ----------+----------
            |
   SW (2)   |   SE (3)
            |
"""


class Rect:
    """Rectangle axe-aligné (AABB)."""
    __slots__ = ("x", "y", "w", "h")

    def __init__(self, x: float, y: float, w: float, h: float):
        self.x = x  # coin haut-gauche
        self.y = y
        self.w = w
        self.h = h

    def contains(self, ball) -> bool:
        """Vrai si le centre de la balle est dans ce rectangle."""
        return (
            self.x <= ball.x < self.x + self.w
            and self.y <= ball.y < self.y + self.h
        )

    def intersects_circle(self, cx: float, cy: float, r: float) -> bool:
        """Vrai si un cercle (cx, cy, r) intersecte ce rectangle."""
        # Point le plus proche du centre du cercle dans le rect
        closest_x = max(self.x, min(cx, self.x + self.w))
        closest_y = max(self.y, min(cy, self.y + self.h))
        dx = cx - closest_x
        dy = cy - closest_y
        return dx * dx + dy * dy <= r * r

    def subdivide(self) -> tuple:
        """Retourne les 4 sous-rectangles (NW, NE, SW, SE)."""
        hw = self.w / 2
        hh = self.h / 2
        return (
            Rect(self.x,      self.y,      hw, hh),  # NW
            Rect(self.x + hw, self.y,      hw, hh),  # NE
            Rect(self.x,      self.y + hh, hw, hh),  # SW
            Rect(self.x + hw, self.y + hh, hw, hh),  # SE
        )


class QuadTree:
    """
    Paramètres :
      boundary  : Rect  — zone couverte par ce nœud
      capacity  : int   — nb max de balles avant subdivision (8 est un bon défaut)
      max_depth : int   — profondeur max pour éviter la récursion infinie
    """

    def __init__(self, boundary: Rect, capacity: int = 8, max_depth: int = 6, _depth: int = 0):
        self.boundary = boundary
        self.capacity = capacity
        self.max_depth = max_depth
        self.depth = _depth

        self.balls: list = []       # balles stockées dans ce nœud
        self.children: list = []    # sous-arbres (vide si feuille)

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------
    def insert(self, ball) -> bool:
        """Insère une balle. Retourne False si hors-limites."""
        if not self.boundary.contains(ball):
            return False

        if not self.children:
            # Nœud feuille
            if len(self.balls) < self.capacity or self.depth >= self.max_depth:
                self.balls.append(ball)
                return True
            else:
                self._subdivide()

        # Nœud interne : on délègue aux enfants
        for child in self.children:
            if child.insert(ball):
                return True

        # Cas rare : balle exactement sur la frontière
        self.balls.append(ball)
        return True

    def _subdivide(self):
        """Divise ce nœud en 4 enfants et redistribue les balles."""
        for rect in self.boundary.subdivide():
            self.children.append(
                QuadTree(rect, self.capacity, self.max_depth, self.depth + 1)
            )
        # Redistribuer les balles existantes
        remaining = []
        for ball in self.balls:
            inserted = False
            for child in self.children:
                if child.insert(ball):
                    inserted = True
                    break
            if not inserted:
                remaining.append(ball)
        self.balls = remaining

    # ------------------------------------------------------------------
    # Requête : toutes les balles dans un rayon (cx, cy, r)
    # ------------------------------------------------------------------
    def query_radius(self, cx: float, cy: float, r: float, found: list = None) -> list:
        """Retourne toutes les balles dont le centre est dans le cercle de requête."""
        if found is None:
            found = []

        if not self.boundary.intersects_circle(cx, cy, r):
            return found

        for ball in self.balls:
            dx = ball.x - cx
            dy = ball.y - cy
            if dx * dx + dy * dy <= r * r:
                found.append(ball)

        for child in self.children:
            child.query_radius(cx, cy, r, found)

        return found

    # ------------------------------------------------------------------
    # Utilitaire : tous les nœuds (pour le debug visuel)
    # ------------------------------------------------------------------
    def all_boundaries(self, result: list = None) -> list:
        if result is None:
            result = []
        result.append(self.boundary)
        for child in self.children:
            child.all_boundaries(result)
        return result
