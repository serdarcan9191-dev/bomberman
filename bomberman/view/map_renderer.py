"""
Map / harita çizimi.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pygame

from model.level import Theme, TileType
from view.characters import load_asset_image


class MapRenderer:
    def __init__(self, tile_size: int = 64) -> None:
        self.tile_size = tile_size
        self._unbreakable_image = load_asset_image("unbreakable.png")
        self._breakable_image = load_asset_image("breakable.png")
        self._hard_image = load_asset_image("hardbreakable.png")
        self._exit_image = load_asset_image("exit.png")
        self._theme_wall_images: dict[Theme, pygame.Surface | None] = {
            Theme.DESERT: load_asset_image("desertwall.png"),
            Theme.FOREST: load_asset_image("treewall.png"),
            Theme.CITY: load_asset_image("citywall.png"),
        }

    def draw(
        self,
        surface: pygame.Surface,
        tiles: Iterable[tuple[int, int, TileType]],
        offset: tuple[int, int] = (0, 0),
        theme: Theme = Theme.CITY,
    ) -> None:
        for x, y, kind in tiles:
            rect = pygame.Rect(
                offset[0] + x * self.tile_size,
                offset[1] + y * self.tile_size,
                self.tile_size,
                self.tile_size,
            )
            if kind == TileType.UNBREAKABLE:
                themed = self._theme_wall_images.get(theme)
                if themed:
                    scaled = pygame.transform.smoothscale(themed, (self.tile_size, self.tile_size))
                    surface.blit(scaled, rect)
                    continue
                if self._unbreakable_image:
                    scaled = pygame.transform.smoothscale(self._unbreakable_image, (self.tile_size, self.tile_size))
                    surface.blit(scaled, rect)
                    continue
            elif kind == TileType.BREAKABLE and self._breakable_image:
                scaled = pygame.transform.smoothscale(self._breakable_image, (self.tile_size, self.tile_size))
                surface.blit(scaled, rect)
            elif kind == TileType.HARD and self._hard_image:
                scaled = pygame.transform.smoothscale(self._hard_image, (self.tile_size, self.tile_size))
                surface.blit(scaled, rect)
            elif kind == TileType.EXIT and self._exit_image:
                scaled = pygame.transform.smoothscale(self._exit_image, (self.tile_size, self.tile_size))
                surface.blit(scaled, rect)
            else:
                color = self._tile_color(kind, theme)
                pygame.draw.rect(surface, color, rect)

    def _tile_color(self, kind: TileType, theme: Theme) -> tuple[int, int, int]:
        colors = self._theme_colors(theme)
        match kind:
            case TileType.EMPTY:
                return colors.empty
            case TileType.UNBREAKABLE:
                return colors.unbreakable
            case TileType.BREAKABLE:
                return colors.breakable
            case TileType.HARD:
                return colors.hard
        return (0, 0, 0)

    @staticmethod
    def _theme_colors(theme: Theme) -> "MapRenderer.ThemeColors":
        match theme:
            case Theme.DESERT:
                return MapRenderer.ThemeColors(
                    empty=(30, 24, 15),
                    unbreakable=(150, 130, 100),
                    breakable=(210, 180, 130),
                    hard=(165, 145, 110),
                )
            case Theme.FOREST:
                return MapRenderer.ThemeColors(
                    empty=(15, 25, 18),
                    unbreakable=(35, 75, 45),
                    breakable=(80, 150, 90),
                    hard=(60, 110, 70),
                )
            case Theme.CITY:
                return MapRenderer.ThemeColors(
                    empty=(12, 15, 25),
                    unbreakable=(60, 60, 80),
                    breakable=(160, 110, 60),
                    hard=(90, 90, 120),
                )
        return MapRenderer.ThemeColors.empty_theme()

    @dataclass(frozen=True)
    class ThemeColors:
        empty: tuple[int, int, int]
        unbreakable: tuple[int, int, int]
        breakable: tuple[int, int, int]
        hard: tuple[int, int, int]

        @staticmethod
        def empty_theme() -> "MapRenderer.ThemeColors":
            return MapRenderer.ThemeColors(
                empty=(0, 0, 0),
                unbreakable=(0, 0, 0),
                breakable=(0, 0, 0),
                hard=(0, 0, 0),
            )

