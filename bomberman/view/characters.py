"""
Karakter modelleri ve fabrikaları (View için).
"""
from __future__ import annotations

import pygame

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

ConfigColor = Tuple[int, int, int]


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    description: str
    accent_color: ConfigColor
    avatar_color: ConfigColor
    tagline: str | None = None
    image_name: str | None = None


class CharacterFactory:
    @staticmethod
    def roster() -> Sequence[Character]:
        return [
            Character(
                id="bomberman",
                name="Bomberman",
                description="Klasik bomba ustası, dengeli hız ve güç.",
                accent_color=(70, 130, 255),
                avatar_color=(25, 50, 120),
                tagline="Patlamaları doğru yerleştiren efsane.",
                image_name="bman.png",
            ),
        ]

    @staticmethod
    def find_by_id(character_id: str) -> Character | None:
        return next((c for c in CharacterFactory.roster() if c.id == character_id), None)


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def load_asset_image(name: str) -> pygame.Surface | None:
    if not name:
        return None
    path = ASSETS_DIR / name
    if not path.exists():
        return None
    return pygame.image.load(path).convert_alpha()


@dataclass(frozen=True)
class Monster:
    id: str
    name: str
    image_name: str
    description: str


class MonsterFactory:
    @staticmethod
    def roster() -> Sequence[Monster]:
        return [
            Monster(
                id="m1",
                name="Static Enemy",
                image_name="senemy.png",
                description="Yavaş, sadece etrafında gezinen canavar.",
            ),
            Monster(
                id="m2",
                name="Chasing Enemy",
                image_name="chenemy.png",
                description="Oyuncuyu gördüğünde takip eden saldırgan.",
            ),
            Monster(
                id="m3",
                name="Smart Enemy",
                image_name="ienemy.png",
                description="Oyuncuyu akıllıca köşeye sıkıştırmaya çalışan düşman.",
            ),
        ]
    
    @staticmethod
    def create(enemy_type: str, position: Tuple[int, int]):
        """Factory Method: Düşman tipi ve pozisyona göre düşman instance'ı oluşturur."""
        from model.enemy import StaticEnemy, ChasingEnemy, SmartEnemy, EnemyType
        
        if enemy_type == "STATIC" or enemy_type == EnemyType.STATIC:
            return StaticEnemy(position)
        elif enemy_type == "CHASING" or enemy_type == EnemyType.CHASING:
            return ChasingEnemy(position)
        elif enemy_type == "SMART" or enemy_type == EnemyType.SMART:
            return SmartEnemy(position)
        else:
            raise ValueError(f"Unknown enemy type: {enemy_type}")


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"


def _load_image(name: str) -> pygame.Surface | None:
    path = ASSETS_DIR / name
    if not path.exists():
        return None
    return pygame.image.load(path).convert_alpha()


class CharacterSprite:
    """Karakteri asset veya stickman ile çizen sınıf."""

    def __init__(self, character: Character) -> None:
        self.character = character
        self.image = load_asset_image(character.image_name) if character.image_name else None

    def draw(self, surface: pygame.Surface, base_rect: pygame.Rect) -> None:
        accent = self.character.accent_color
        body_color = self.character.avatar_color

        if self.image is not None:
            scaled = pygame.transform.smoothscale(self.image, (int(base_rect.width), int(base_rect.height)))
            surface.blit(scaled, base_rect)
            return

        head_center = (base_rect.centerx, base_rect.top + base_rect.height * 0.2)
        head_radius = base_rect.width // 8
        pygame.draw.circle(surface, accent, head_center, head_radius)
        pygame.draw.circle(surface, (255, 255, 255), (head_center[0] - head_radius // 2, head_center[1]), 2)
        pygame.draw.circle(surface, (255, 255, 255), (head_center[0] + head_radius // 2, head_center[1]), 2)

        body_start = (head_center[0], head_center[1] + head_radius)
        body_end = (head_center[0], base_rect.bottom - base_rect.height * 0.15)
        pygame.draw.line(surface, body_color, body_start, body_end, 4)

        arm_length = base_rect.width * 0.4
        arm_y = head_center[1] + head_radius * 1.2
        pygame.draw.line(surface, accent, (body_start[0] - arm_length, arm_y), (body_start[0] + arm_length, arm_y), 4)

        leg_height = base_rect.height * 0.35
        left_foot = (body_end[0] - leg_height * 0.5, body_end[1] + leg_height)
        right_foot = (body_end[0] + leg_height * 0.5, body_end[1] + leg_height)
        pygame.draw.line(surface, body_color, body_end, left_foot, 4)
        pygame.draw.line(surface, body_color, body_end, right_foot, 4)

        # küçük bomba çizgisi
        bomb_rect = pygame.Rect(
            base_rect.centerx - base_rect.width * 0.1,
            base_rect.bottom - base_rect.height * 0.25,
            base_rect.width * 0.2,
            base_rect.height * 0.2,
        )
        pygame.draw.ellipse(surface, accent, bomb_rect)
        fuse = (bomb_rect.centerx, bomb_rect.top)
        pygame.draw.line(surface, (255, 220, 0), fuse, (fuse[0], fuse[1] - 10), 2)

