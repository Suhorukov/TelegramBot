"""Игровая логика для игры с шариками (без UI)."""

from __future__ import annotations

import colorsys
import math
import random
from dataclasses import dataclass, field
from typing import Iterable


Vec2 = tuple[float, float]
RGB = tuple[int, int, int]


@dataclass
class Ball:
    """Шарик на игровом поле."""

    x: float
    y: float
    vx: float
    vy: float
    radius: float
    color: RGB
    id: int | None = None

    def position(self) -> Vec2:
        return self.x, self.y

    def velocity(self) -> Vec2:
        return self.vx, self.vy

    def copy(self) -> Ball:
        return Ball(
            x=self.x,
            y=self.y,
            vx=self.vx,
            vy=self.vy,
            radius=self.radius,
            color=self.color,
            id=self.id,
        )


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rgb_to_hsv(color: RGB) -> tuple[float, float, float]:
    r, g, b = (channel / 255.0 for channel in color)
    return colorsys.rgb_to_hsv(r, g, b)


def _hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _circular_hue_mean(hues: Iterable[float], weights: Iterable[float]) -> float:
    """Среднее по кругу оттенка — корректно смешивает красный и фиолетовый."""
    sin_sum = 0.0
    cos_sum = 0.0
    for hue, weight in zip(hues, weights, strict=True):
        angle = hue * 2.0 * math.pi
        sin_sum += math.sin(angle) * weight
        cos_sum += math.cos(angle) * weight
    if abs(sin_sum) < 1e-9 and abs(cos_sum) < 1e-9:
        return hues[0] if hues else 0.0
    angle = math.atan2(sin_sum, cos_sum)
    if angle < 0:
        angle += 2.0 * math.pi
    return angle / (2.0 * math.pi)


def mix_colors(color_a: RGB, color_b: RGB, ratio: float = 0.5) -> RGB:
    """
    Смешивает два цвета как пигменты.

    Результат насыщенный и выразительный: белый почти не появляется,
    вместо этого получаются глубокие оттенки и «грязные» переходы.
    """
    ratio = _clamp(ratio, 0.0, 1.0)

    # Пигментное смешение в RGB — темнее и насыщеннее, чем простое усреднение.
    pigment_a = tuple((channel / 255.0) ** 0.85 for channel in color_a)
    pigment_b = tuple((channel / 255.0) ** 0.85 for channel in color_b)
    pigment = tuple(
        (a ** (1.0 - ratio)) * (b**ratio) for a, b in zip(pigment_a, pigment_b, strict=True)
    )
    pigment_rgb = tuple(int(_clamp(channel ** (1.0 / 0.85), 0.0, 1.0) * 255) for channel in pigment)

    # Дополнительно подмешиваем оттенок по HSV, чтобы цвета «играли» интереснее.
    h_a, s_a, v_a = _rgb_to_hsv(color_a)
    h_b, s_b, v_b = _rgb_to_hsv(color_b)
    hue = _circular_hue_mean((h_a, h_b), (1.0 - ratio, ratio))
    saturation = _clamp(max(s_a, s_b) * 0.75 + 0.2, 0.35, 1.0)
    value = _clamp(min(v_a, v_b) * 0.9 + 0.05, 0.12, 0.82)

    hsv_rgb = _hsv_to_rgb(hue, saturation, value)

    # Берём более тёмный из двух подходов — так белый почти не возникает.
    return tuple(min(p, h) for p, h in zip(pigment_rgb, hsv_rgb, strict=True))


def distance(a: Vec2, b: Vec2) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def random_bright_color() -> RGB:
    """Случайный яркий цвет для стартовых шариков."""
    hue = random.random()
    return _hsv_to_rgb(hue, random.uniform(0.65, 1.0), random.uniform(0.75, 0.95))


@dataclass
class GameConfig:
    width: float = 800.0
    height: float = 800.0
    suck_radius: float = 90.0
    suck_capture_distance: float = 18.0
    suck_pull_strength: float = 420.0
    spit_speed: float = 260.0
    wall_bounce_damping: float = 0.92
    min_speed: float = 35.0
    max_speed: float = 320.0
    mix_overlap_threshold: float = 0.35


@dataclass
class GameState:
    """Состояние игры: поле, шарики, инвентарь, положение мыши."""

    balls: list[Ball] = field(default_factory=list)
    inventory: list[Ball] = field(default_factory=list)
    mouse_x: float = 0.0
    mouse_y: float = 0.0
    sucking: bool = False
    spitting: bool = False
    next_ball_id: int = 1

    def active_balls(self) -> list[Ball]:
        return self.balls


class GameLogic:
    """Вся игровая логика: движение, всасывание, выплёвывание, смешивание цветов."""

    def __init__(self, config: GameConfig | None = None) -> None:
        self.config = config or GameConfig()
        self.state = GameState()

    def add_ball(
        self,
        x: float,
        y: float,
        *,
        vx: float | None = None,
        vy: float | None = None,
        radius: float = 18.0,
        color: RGB | None = None,
    ) -> Ball:
        if vx is None:
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(self.config.min_speed, self.config.max_speed * 0.6)
            vx = math.cos(angle) * speed
        if vy is None:
            angle = random.uniform(0.0, 2.0 * math.pi)
            speed = random.uniform(self.config.min_speed, self.config.max_speed * 0.6)
            vy = math.sin(angle) * speed

        ball = Ball(
            x=x,
            y=y,
            vx=vx,
            vy=vy,
            radius=radius,
            color=color or random_bright_color(),
            id=self.state.next_ball_id,
        )
        self.state.next_ball_id += 1
        self.state.balls.append(ball)
        return ball

    def populate(self, count: int) -> None:
        margin = 40.0
        for _ in range(count):
            x = random.uniform(margin, self.config.width - margin)
            y = random.uniform(margin, self.config.height - margin)
            self.add_ball(x, y)

    def set_mouse(self, x: float, y: float) -> None:
        self.state.mouse_x = x
        self.state.mouse_y = y

    def set_sucking(self, active: bool) -> None:
        self.state.sucking = active

    def set_spitting(self, active: bool) -> None:
        self.state.spitting = active

    def update(self, dt: float) -> None:
        """Один шаг симуляции."""
        if dt <= 0:
            return

        self._apply_suck(dt)
        self._apply_spit()
        self._move_balls(dt)
        self._mix_overlapping_colors()
        self._limit_speeds()

    def _apply_suck(self, dt: float) -> None:
        if not self.state.sucking:
            return

        mouse = (self.state.mouse_x, self.state.mouse_y)
        captured: list[Ball] = []

        for ball in self.state.balls:
            dist = distance(ball.position(), mouse)
            if dist > self.config.suck_radius:
                continue

            if dist <= self.config.suck_capture_distance + ball.radius * 0.25:
                captured.append(ball)
                continue

            pull = self.config.suck_pull_strength * (1.0 - dist / self.config.suck_radius)
            if dist < 1e-6:
                continue
            nx = (mouse[0] - ball.x) / dist
            ny = (mouse[1] - ball.y) / dist
            ball.vx += nx * pull * dt
            ball.vy += ny * pull * dt

        for ball in captured:
            self.state.balls.remove(ball)
            stored = ball.copy()
            stored.vx = 0.0
            stored.vy = 0.0
            self.state.inventory.append(stored)

    def _apply_spit(self) -> None:
        if not self.state.spitting or not self.state.inventory:
            return

        ball = self.state.inventory.pop(0)
        ball.x = self.state.mouse_x
        ball.y = self.state.mouse_y

        angle = random.uniform(0.0, 2.0 * math.pi)
        ball.vx = math.cos(angle) * self.config.spit_speed
        ball.vy = math.sin(angle) * self.config.spit_speed
        self.state.balls.append(ball)
        self.state.spitting = False

    def spit_ball(self, direction: Vec2 | None = None) -> Ball | None:
        """Выплюнуть один шарик из инвентаря в заданном направлении."""
        if not self.state.inventory:
            return None

        ball = self.state.inventory.pop(0)
        ball.x = self.state.mouse_x
        ball.y = self.state.mouse_y

        if direction is None:
            angle = random.uniform(0.0, 2.0 * math.pi)
            ball.vx = math.cos(angle) * self.config.spit_speed
            ball.vy = math.sin(angle) * self.config.spit_speed
        else:
            length = math.hypot(direction[0], direction[1])
            if length < 1e-6:
                ball.vx = self.config.spit_speed
                ball.vy = 0.0
            else:
                ball.vx = direction[0] / length * self.config.spit_speed
                ball.vy = direction[1] / length * self.config.spit_speed

        self.state.balls.append(ball)
        return ball

    def suck_nearest(self) -> Ball | None:
        """Немедленно всосать ближайший шарик в радиусе (удобно для UI-клика)."""
        mouse = (self.state.mouse_x, self.state.mouse_y)
        candidates = [
            ball
            for ball in self.state.balls
            if distance(ball.position(), mouse) <= self.config.suck_radius
        ]
        if not candidates:
            return None

        nearest = min(candidates, key=lambda ball: distance(ball.position(), mouse))
        self.state.balls.remove(nearest)
        stored = nearest.copy()
        stored.vx = 0.0
        stored.vy = 0.0
        self.state.inventory.append(stored)
        return stored

    def _move_balls(self, dt: float) -> None:
        width = self.config.width
        height = self.config.height
        damping = self.config.wall_bounce_damping

        for ball in self.state.balls:
            ball.x += ball.vx * dt
            ball.y += ball.vy * dt

            if ball.x - ball.radius < 0:
                ball.x = ball.radius
                ball.vx = abs(ball.vx) * damping
            elif ball.x + ball.radius > width:
                ball.x = width - ball.radius
                ball.vx = -abs(ball.vx) * damping

            if ball.y - ball.radius < 0:
                ball.y = ball.radius
                ball.vy = abs(ball.vy) * damping
            elif ball.y + ball.radius > height:
                ball.y = height - ball.radius
                ball.vy = -abs(ball.vy) * damping

    def _mix_overlapping_colors(self) -> None:
        """При пересечении шарики смешивают цвет; отталкивания нет."""
        balls = self.state.balls
        threshold = self.config.mix_overlap_threshold

        for i in range(len(balls)):
            for j in range(i + 1, len(balls)):
                a = balls[i]
                b = balls[j]
                dist = distance(a.position(), b.position())
                overlap = (a.radius + b.radius) - dist
                if overlap <= 0:
                    continue

                overlap_ratio = _clamp(overlap / (a.radius + b.radius), 0.0, 1.0)
                if overlap_ratio < threshold:
                    continue

                mix_amount = _clamp(overlap_ratio * 0.18, 0.04, 0.22)
                mixed = mix_colors(a.color, b.color, ratio=0.5)
                a.color = mix_colors(a.color, mixed, ratio=mix_amount)
                b.color = mix_colors(b.color, mixed, ratio=mix_amount)

    def _limit_speeds(self) -> None:
        max_speed = self.config.max_speed
        min_speed = self.config.min_speed

        for ball in self.state.balls:
            speed = math.hypot(ball.vx, ball.vy)
            if speed > max_speed:
                scale = max_speed / speed
                ball.vx *= scale
                ball.vy *= scale
            elif speed < min_speed:
                if speed < 1e-6:
                    angle = random.uniform(0.0, 2.0 * math.pi)
                    ball.vx = math.cos(angle) * min_speed
                    ball.vy = math.sin(angle) * min_speed
                else:
                    scale = min_speed / speed
                    ball.vx *= scale
                    ball.vy *= scale

    def balls_in_suck_range(self) -> list[Ball]:
        mouse = (self.state.mouse_x, self.state.mouse_y)
        return [
            ball
            for ball in self.state.balls
            if distance(ball.position(), mouse) <= self.config.suck_radius
        ]
