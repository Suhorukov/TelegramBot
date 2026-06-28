"""Графический интерфейс для игры с шариками."""

from __future__ import annotations

import sys

import pygame

from logic import Ball, GameConfig, GameLogic, RGB

# --- Настраиваемые параметры ---
INITIAL_BALL_COUNT = 15
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60

DELETE_ZONE_WIDTH = 110
DELETE_ZONE_HEIGHT = 110

BACKGROUND_COLOR = (255, 255, 255)
DELETE_ZONE_COLOR = (255, 230, 230)
DELETE_ZONE_BORDER = (220, 80, 80)
SUCK_RING_COLOR = (120, 120, 200, 60)
HUD_COLOR = (60, 60, 60)
INVENTORY_SLOT_SIZE = 28
INVENTORY_PADDING = 10


def rgb_to_pygame(color: RGB) -> tuple[int, int, int]:
    return color[0], color[1], color[2]


def draw_ball(surface: pygame.Surface, ball: Ball) -> None:
    center = (int(ball.x), int(ball.y))
    radius = int(ball.radius)
    color = rgb_to_pygame(ball.color)

    pygame.draw.circle(surface, color, center, radius)
    highlight = tuple(min(255, channel + 40) for channel in color)
    pygame.draw.circle(surface, highlight, (center[0] - radius // 3, center[1] - radius // 3), max(2, radius // 4))


def draw_delete_zone(surface: pygame.Surface) -> pygame.Rect:
    zone = pygame.Rect(
        WINDOW_WIDTH - DELETE_ZONE_WIDTH,
        WINDOW_HEIGHT - DELETE_ZONE_HEIGHT,
        DELETE_ZONE_WIDTH,
        DELETE_ZONE_HEIGHT,
    )
    pygame.draw.rect(surface, DELETE_ZONE_COLOR, zone, border_radius=8)
    pygame.draw.rect(surface, DELETE_ZONE_BORDER, zone, width=2, border_radius=8)

    font = pygame.font.SysFont(None, 22)
    label = font.render("Удалить", True, DELETE_ZONE_BORDER)
    surface.blit(label, label.get_rect(center=zone.center))
    return zone


def draw_suck_radius(surface: pygame.Surface, game: GameLogic, sucking: bool) -> None:
    if not sucking:
        return

    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(
        overlay,
        SUCK_RING_COLOR,
        (int(game.state.mouse_x), int(game.state.mouse_y)),
        int(game.config.suck_radius),
        width=2,
    )
    pygame.draw.circle(
        overlay,
        (100, 100, 200, 30),
        (int(game.state.mouse_x), int(game.state.mouse_y)),
        int(game.config.suck_radius),
    )
    surface.blit(overlay, (0, 0))


def draw_inventory(surface: pygame.Surface, inventory: list[Ball]) -> None:
    if not inventory:
        return

    panel_height = INVENTORY_SLOT_SIZE + INVENTORY_PADDING * 2
    panel = pygame.Rect(10, 10, WINDOW_WIDTH - 20, panel_height)
    pygame.draw.rect(surface, (245, 245, 245), panel, border_radius=8)
    pygame.draw.rect(surface, (200, 200, 200), panel, width=1, border_radius=8)

    font = pygame.font.SysFont(None, 22)
    label = font.render(f"Инвентарь: {len(inventory)}", True, HUD_COLOR)
    surface.blit(label, (panel.x + INVENTORY_PADDING, panel.y + INVENTORY_PADDING // 2))

    x = panel.x + 130
    y = panel.y + INVENTORY_PADDING
    for ball in inventory[:20]:
        pygame.draw.circle(
            surface,
            rgb_to_pygame(ball.color),
            (x + INVENTORY_SLOT_SIZE // 2, y + INVENTORY_SLOT_SIZE // 2),
            INVENTORY_SLOT_SIZE // 2 - 2,
        )
        x += INVENTORY_SLOT_SIZE + 6


def draw_hud(surface: pygame.Surface, inventory_count: int) -> None:
    font = pygame.font.SysFont(None, 24)
    hints = [
        "ЛКМ — всасывать",
        "ПКМ — выплюнуть",
        f"В инвентаре: {inventory_count}",
    ]
    y = WINDOW_HEIGHT - 70
    for text in hints:
        surface.blit(font.render(text, True, HUD_COLOR), (16, y))
        y += 22


def remove_balls_in_zone(game: GameLogic, zone: pygame.Rect) -> int:
    removed = 0
    for ball in game.state.balls[:]:
        if zone.collidepoint(ball.x, ball.y):
            game.state.balls.remove(ball)
            removed += 1
    return removed


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Шарики")
    clock = pygame.time.Clock()

    config = GameConfig(width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    game = GameLogic(config)
    game.populate(INITIAL_BALL_COUNT)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                game.set_mouse(*event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game.set_mouse(*event.pos)
                if event.button == 1:
                    game.set_sucking(True)
                elif event.button == 3 and game.state.inventory:
                    mx, my = event.pos
                    game.spit_ball(direction=(mx - game.state.mouse_x, my - game.state.mouse_y))
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    game.set_sucking(False)

        mouse_pressed = pygame.mouse.get_pressed()
        game.set_sucking(bool(mouse_pressed[0]))
        game.set_mouse(*pygame.mouse.get_pos())

        game.update(dt)
        delete_zone = pygame.Rect(
            WINDOW_WIDTH - DELETE_ZONE_WIDTH,
            WINDOW_HEIGHT - DELETE_ZONE_HEIGHT,
            DELETE_ZONE_WIDTH,
            DELETE_ZONE_HEIGHT,
        )
        remove_balls_in_zone(game, delete_zone)

        screen.fill(BACKGROUND_COLOR)
        draw_delete_zone(screen)
        draw_suck_radius(screen, game, game.state.sucking)

        for ball in game.state.balls:
            draw_ball(screen, ball)

        draw_inventory(screen, game.state.inventory)
        draw_hud(screen, len(game.state.inventory))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()
        sys.exit(0)
