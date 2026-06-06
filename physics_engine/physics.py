"""
physics.py
==========
Moteur physique. Utilise le Quadtree pour les collisions balle-balle.
"""

import math
import random

from quadtree import QuadTree, Rect


class Ball:
    def __init__(self, x, y, radius=None, mass=None, vx=None, vy=None, sprite=None):
        self.x = x
        self.y = y
        self.radius  = radius if radius is not None else random.uniform(8, 22)
        self.mass    = mass   if mass   is not None else math.pi * self.radius ** 2

        self.vx = vx if vx is not None else random.uniform(-300, 300)
        self.vy = vy if vy is not None else random.uniform(-200, 100)

        # Sprite optionnel (nom de fichier sans extension, ex : "rock")
        # Si None → rendu par défaut avec couleur vitesse
        self.sprite: str | None = sprite

        # Trail
        self.trail: list[tuple] = []
        self.trail_max: int = 18

        # Angle de rotation du sprite (degrés) — interpolé pour éviter le flickering
        self.angle_deg: float = 0.0

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx ** 2 + self.vy ** 2)

    def update_trail(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.trail_max:
            self.trail.pop(0)


class World:
    """Contient toutes les balles et applique la physique."""

    GRAVITY     = 800    # px/s²
    RESTITUTION = 0.75   # coefficient de rebond
    FRICTION    = 0.995  # frottement de l'air par frame

    def __init__(self, width: int, height: int):
        self.width  = width
        self.height = height
        self.balls: list[Ball] = []

        # Quadtree conservé entre les frames et exposé au renderer (debug)
        self._boundary = Rect(0, 0, width, height)
        self.qt: QuadTree = QuadTree(self._boundary)

        # Rayon max réel des balles (mis à jour à chaque add_ball)
        self._max_radius: float = 22.0

    def add_ball(self, ball: Ball):
        self.balls.append(ball)
        if ball.radius > self._max_radius:
            self._max_radius = ball.radius

    def update(self, dt: float):
        for ball in self.balls:
            ball.update_trail()

            ball.vy += self.GRAVITY * dt
            ball.vx *= self.FRICTION
            ball.vy *= self.FRICTION

            ball.x  += ball.vx * dt
            ball.y  += ball.vy * dt

            self._border_collision(ball)

        self._ball_collisions_quadtree()

    # ------------------------------------------------------------------
    # Collisions avec les bords
    # ------------------------------------------------------------------
    def _border_collision(self, ball: Ball):
        r = ball.radius

        if ball.x - r < 0:
            ball.x  = r
            ball.vx = abs(ball.vx) * self.RESTITUTION
        elif ball.x + r > self.width:
            ball.x  = self.width - r
            ball.vx = -abs(ball.vx) * self.RESTITUTION

        if ball.y - r < 0:
            ball.y  = r
            ball.vy = abs(ball.vy) * self.RESTITUTION
        elif ball.y + r > self.height:
            ball.y  = self.height - r
            ball.vy = -abs(ball.vy) * self.RESTITUTION
            ball.vx *= 0.92

    # ------------------------------------------------------------------
    # Collisions balle-balle avec Quadtree — O(n log n)
    # ------------------------------------------------------------------
    def _build_quadtree(self):
        """Reconstruit le Quadtree depuis zéro. Appelé une seule fois par frame."""
        self.qt = QuadTree(self._boundary, capacity=8, max_depth=6)
        for ball in self.balls:
            self.qt.insert(ball)

    def _ball_collisions_quadtree(self):
        self._build_quadtree()   # une seule construction par frame

        # Dict id(ball) → indice — O(1) à la place de list.index() qui est O(n)
        idx_of = {id(b): i for i, b in enumerate(self.balls)}
        checked: set[tuple[int, int]] = set()

        for i, a in enumerate(self.balls):
            # Rayon de recherche = rayon de a + rayon max réel
            search_r = a.radius + self._max_radius
            candidates = self.qt.query_radius(a.x, a.y, search_r)

            for b in candidates:
                if b is a:
                    continue
                j = idx_of[id(b)]
                pair = (i, j) if i < j else (j, i)
                if pair in checked:
                    continue
                checked.add(pair)
                self._resolve_collision(a, b)

    def _resolve_collision(self, a: Ball, b: Ball):
        dx   = b.x - a.x
        dy   = b.y - a.y
        dist = math.sqrt(dx * dx + dy * dy)
        min_dist = a.radius + b.radius

        if dist >= min_dist or dist == 0:
            return

        overlap    = (min_dist - dist) / 2
        nx, ny     = dx / dist, dy / dist
        total_mass = a.mass + b.mass

        a.x -= nx * overlap * (b.mass / total_mass)
        a.y -= ny * overlap * (b.mass / total_mass)
        b.x += nx * overlap * (a.mass / total_mass)
        b.y += ny * overlap * (a.mass / total_mass)

        dvx = a.vx - b.vx
        dvy = a.vy - b.vy
        dot = dvx * nx + dvy * ny

        if dot > 0:
            impulse = (2 * dot / total_mass) * self.RESTITUTION
            a.vx -= impulse * b.mass * nx
            a.vy -= impulse * b.mass * ny
            b.vx += impulse * a.mass * nx
            b.vy += impulse * a.mass * ny
