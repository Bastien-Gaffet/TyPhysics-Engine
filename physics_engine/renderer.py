"""
renderer.py
===========
Rendu visuel : couleurs par vitesse, trails, bloom, sprites PNG custom.

Système de sprites :
  - Place tes PNG dans le dossier  assets/
  - Nommez-les simplement :        assets/rock.png, assets/coin.png, etc.
  - Pour créer une balle avec un sprite :
        Ball(x, y, radius=24, sprite="rock")
  - L'image est redimensionnée automatiquement au diamètre de la balle.
  - Elle tourne en fonction de la direction du mouvement (optionnel).
  - Si le fichier n'existe pas → rendu par défaut (cercle coloré).
"""

import os
import math
import pygame


# ------------------------------------------------------------------
# Palette couleur → vitesse
# ------------------------------------------------------------------
SPEED_COLORS = [
    (0,   30,  80),
    (0,   100, 200),
    (0,   200, 180),
    (100, 220, 50),
    (255, 180, 0),
    (255, 50,  30),
]
MAX_SPEED = 1200


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def speed_to_color(speed: float) -> tuple:
    t = min(speed / MAX_SPEED, 1.0) * (len(SPEED_COLORS) - 1)
    idx = int(t)
    frac = t - idx
    if idx >= len(SPEED_COLORS) - 1:
        return SPEED_COLORS[-1]
    return lerp_color(SPEED_COLORS[idx], SPEED_COLORS[idx + 1], frac)


# ------------------------------------------------------------------
# Effets visuels
# ------------------------------------------------------------------
def draw_glow(surface, color, center, radius, intensity=0.4):
    glow_surf = pygame.Surface((int(radius * 6), int(radius * 6)), pygame.SRCALPHA)
    gx, gy = int(radius * 3), int(radius * 3)
    for i in range(5, 0, -1):
        r     = int(radius * (1 + i * 0.5))
        alpha = int(intensity * 255 / (i + 1))
        pygame.draw.circle(glow_surf, (*color, alpha), (gx, gy), r)
    surface.blit(glow_surf, (int(center[0] - radius * 3), int(center[1] - radius * 3)))


def draw_trail(surface, trail, color, radius):
    n = len(trail)
    for i, (tx, ty) in enumerate(trail):
        t      = i / n
        alpha  = int(t * 160)
        tr     = max(1, int(radius * t * 0.7))
        s      = pygame.Surface((tr * 2 + 1, tr * 2 + 1), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, alpha), (tr, tr), tr)
        surface.blit(s, (int(tx) - tr, int(ty) - tr))


# ------------------------------------------------------------------
# Gestionnaire de sprites
# ------------------------------------------------------------------
class SpriteCache:
    """
    Charge et met en cache les sprites PNG.
    Les images sont redimensionnées à la demande (par diamètre).
    """

    ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

    def __init__(self):
        # cache[name][diameter] = Surface pygame
        self._cache: dict[str, dict[int, pygame.Surface]] = {}

    def get(self, name: str, diameter: int) -> pygame.Surface | None:
        """
        Retourne la surface pour (name, diameter).
        Retourne None si le fichier n'existe pas.
        """
        if name not in self._cache:
            path = os.path.join(self.ASSETS_DIR, f"{name}.png")
            if not os.path.isfile(path):
                self._cache[name] = None   # marquer comme introuvable
                print(f"[SpriteCache] Image non trouvée : {path}")
                return None
            try:
                raw = pygame.image.load(path).convert_alpha()
                self._cache[name] = {"_raw": raw}
            except Exception as e:
                print(f"[SpriteCache] Erreur chargement {path} : {e}")
                self._cache[name] = None
                return None

        if self._cache[name] is None:
            return None

        if diameter not in self._cache[name]:
            raw    = self._cache[name]["_raw"]
            scaled = pygame.transform.smoothscale(raw, (diameter, diameter))
            self._cache[name][diameter] = scaled

        return self._cache[name][diameter]

    def get_rotated(self, name: str, diameter: int, angle_deg: float) -> pygame.Surface | None:
        """Retourne le sprite tourné de angle_deg degrés (sens horaire)."""
        base = self.get(name, diameter)
        if base is None:
            return None
        return pygame.transform.rotate(base, -angle_deg)


# ------------------------------------------------------------------
# Renderer principal
# ------------------------------------------------------------------
class Renderer:
    BACKGROUND  = (8, 8, 18)
    TEXT_COLOR  = (160, 160, 200)
    DEBUG_COLOR = (40, 60, 40)    # couleur des bordures Quadtree (debug)

    def __init__(self, screen: pygame.Surface):
        self.screen  = screen
        self.font    = pygame.font.SysFont("monospace", 16)
        self.width   = screen.get_width()
        self.height  = screen.get_height()
        self.sprites = SpriteCache()

        self.show_quadtree = False   # debug : affiche la grille du Quadtree

    def clear(self):
        self.screen.fill(self.BACKGROUND)

    # ------------------------------------------------------------------
    # Dessin d'une balle (sprite ou cercle coloré)
    # ------------------------------------------------------------------

    # Vitesse minimale pour déclencher une rotation (évite le flickering au repos)
    _ROTATION_SPEED_THRESHOLD = 80   # px/s
    # Facteur de lissage angulaire : 0 = pas de rotation, 1 = instantané
    # 0.15 = l'angle rattrape ~85% de l'écart en ~10 frames → doux mais réactif
    _ROTATION_LERP = 0.15

    def _update_angle(self, ball) -> float:
        """Calcule et lisse l'angle de rotation du sprite. Retourne l'angle final."""
        if ball.speed < self._ROTATION_SPEED_THRESHOLD:
            # Vitesse trop faible : on ne met pas à jour, on garde l'angle actuel
            return ball.angle_deg

        target = math.degrees(math.atan2(ball.vy, ball.vx))

        # Calcul du delta angulaire le plus court (wrap entre -180 et +180)
        delta = (target - ball.angle_deg + 180) % 360 - 180

        ball.angle_deg += delta * self._ROTATION_LERP
        ball.angle_deg %= 360
        return ball.angle_deg

    def draw_ball(self, ball, glow: bool = True):
        color = speed_to_color(ball.speed)
        cx, cy = int(ball.x), int(ball.y)
        r      = int(ball.radius)
        diam   = r * 2

        # --- Trainée ---
        if ball.trail:
            draw_trail(self.screen, ball.trail, color, ball.radius)

        # --- Glow ---
        if glow and ball.speed > 50:
            draw_glow(self.screen, color, (cx, cy), r, intensity=0.35)

        # --- Sprite ou cercle ---
        if ball.sprite:
            angle = self._update_angle(ball)
            surf  = self.sprites.get_rotated(ball.sprite, diam, angle)
            if surf is not None:
                rect = surf.get_rect(center=(cx, cy))
                self.screen.blit(surf, rect)
                return  # pas de cercle par-dessus

        # Rendu par défaut : cercle coloré + reflet
        pygame.draw.circle(self.screen, color, (cx, cy), r)
        hl_r   = max(2, r // 3)
        hl_pos = (cx - r // 4, cy - r // 4)
        hl_c   = tuple(min(255, c + 120) for c in color)
        pygame.draw.circle(self.screen, hl_c, hl_pos, hl_r)

    # ------------------------------------------------------------------
    # Debug Quadtree
    # ------------------------------------------------------------------
    def draw_quadtree(self, qt):
        """Dessine toutes les cellules du Quadtree (mode debug, touche Q)."""
        for boundary in qt.all_boundaries():
            pygame.draw.rect(
                self.screen, self.DEBUG_COLOR,
                (int(boundary.x), int(boundary.y), int(boundary.w), int(boundary.h)),
                1
            )

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def draw_hud(self, fps: float, ball_count: int):
        lines = [
            f"FPS    : {fps:.0f}",
            f"Balles : {ball_count}",
            "",
            "Clic gauche  → ajouter une balle",
            "Clic droit   → supprimer la plus proche",
            "R            → réinitialiser",
            "G            → gravité on/off",
            "Q            → debug Quadtree",
            "Espace       → pause",
        ]
        for i, line in enumerate(lines):
            surf = self.font.render(line, True, self.TEXT_COLOR)
            self.screen.blit(surf, (12, 12 + i * 20))

    def present(self):
        pygame.display.flip()
