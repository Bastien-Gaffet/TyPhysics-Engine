"""
Physics Engine — main.py
========================
Lancement : python main.py

Dépendance : pip install pygame
"""

import sys
import math
import random
import pygame
import os

from physics  import World, Ball
from renderer import Renderer


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
WIDTH, HEIGHT  = 1200, 750
FPS_CAP        = 120
INITIAL_BALLS  = 30

# Liste de sprites disponibles dans assets/ (sans extension).
# Si vide ou si le fichier n'existe pas → cercle coloré par défaut.
# Exemple : SPRITE_POOL = ["rock", "coin", "star"]
# Chemin absolu vers le dossier assets/, relatif à main.py lui-même
_HERE       = os.path.dirname(os.path.abspath(__file__))
_ASSETS_DIR = os.path.join(_HERE, "assets")

SPRITE_POOL: list[str] = []
if os.path.isdir(_ASSETS_DIR):
    SPRITE_POOL = [f[:-4] for f in os.listdir(_ASSETS_DIR) if f.endswith(".png")]

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def spawn_ball(world: World, x: float = None, y: float = None) -> Ball:
    x = x if x is not None else random.uniform(50, world.width  - 50)
    y = y if y is not None else random.uniform(50, world.height // 2)
    sprite = random.choice(SPRITE_POOL) if SPRITE_POOL else None
    ball   = Ball(x, y, sprite=sprite)
    world.add_ball(ball)
    return ball


def find_closest_ball(world: World, mx: float, my: float) -> Ball | None:
    closest, min_dist = None, float("inf")
    for ball in world.balls:
        d = math.sqrt((ball.x - mx) ** 2 + (ball.y - my) ** 2)
        if d < min_dist:
            min_dist, closest = d, ball
    return closest


def reset_world(world: World):
    world.balls.clear()
    for _ in range(INITIAL_BALLS):
        spawn_ball(world)


# ------------------------------------------------------------------
# Boucle principale
# ------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Physics Engine")
    clock  = pygame.time.Clock()

    world    = World(WIDTH, HEIGHT)
    renderer = Renderer(screen)

    reset_world(world)

    paused  = False
    gravity = True

    while True:
        dt = clock.tick(FPS_CAP) / 1000.0
        dt = min(dt, 0.05)

        # ------ Événements ------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    paused = not paused

                elif event.key == pygame.K_r:
                    reset_world(world)

                elif event.key == pygame.K_g:
                    gravity = not gravity
                    world.GRAVITY = 800 if gravity else 0

                elif event.key == pygame.K_q:
                    renderer.show_quadtree = not renderer.show_quadtree

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if event.button == 1:
                    spawn_ball(world, mx, my)
                elif event.button == 3:
                    target = find_closest_ball(world, mx, my)
                    if target:
                        world.balls.remove(target)

        # ------ Physique ------
        if not paused:
            world.update(dt)

        # ------ Rendu ------
        renderer.clear()

        # Debug Quadtree (touche Q) — réutilise le qt déjà construit par la physique
        if renderer.show_quadtree and world.balls:
            renderer.draw_quadtree(world.qt)

        for ball in world.balls:
            renderer.draw_ball(ball, glow=True)

        renderer.draw_hud(clock.get_fps(), len(world.balls))

        if paused:
            font = pygame.font.SysFont("monospace", 48, bold=True)
            surf = font.render("PAUSE", True, (200, 200, 255))
            screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, HEIGHT // 2 - 30))

        renderer.present()


if __name__ == "__main__":
    main()
