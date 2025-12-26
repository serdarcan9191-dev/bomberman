from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence, Tuple

from model.tile import Tile, TileType
from service.map_generator import MapGenerator


class Theme(Enum):
    DESERT = "desert"
    FOREST = "forest"
    CITY = "city"


DEFAULT_WIDTH = 11
DEFAULT_HEIGHT = 9


@dataclass(frozen=True)
class LevelConfig:
    id: str
    width: int
    height: int
    theme: Theme
    tiles: Sequence[Tile]
    player_start: Tuple[int, int]
    enemy_positions: Sequence[Tuple[int, int]]
    enemy_spawns: Sequence[dict[str, int]]
    explosion_damage: int

    def tile_at(self, x: int, y: int) -> TileType:
        idx = next((t for t in self.tiles if t.x == x and t.y == y), None)
        return idx.type if idx else TileType.EMPTY


@dataclass(frozen=True)
class LevelDefinition:
    id: str
    width: int
    height: int
    theme: Theme
    player_start: Tuple[int, int]
    enemy_positions: Tuple[Tuple[int, int], ...]
    exit_position: Tuple[int, int]
    breakable_positions: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    hard_positions: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    extra_unbreakable: Tuple[Tuple[int, int], ...] = field(default_factory=tuple)
    exit_guard: int = 2
    enemy_spawns: Tuple[dict[str, int], ...] = field(default_factory=tuple)
    explosion_damage: int = 20

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LevelDefinition":
        theme_value = data.get("theme", "city")
        return LevelDefinition(
            id=data["id"],
            width=int(data.get("width", DEFAULT_WIDTH)),
            height=int(data.get("height", DEFAULT_HEIGHT)),
            theme=Theme(theme_value.lower()),
            player_start=tuple(data.get("player_start", (1, 1))),
            enemy_positions=tuple(tuple(pos) for pos in data.get("enemy_positions", [])),
            exit_position=tuple(data["exit_position"]),
            breakable_positions=tuple(tuple(pos) for pos in data.get("breakable_positions", [])),
            hard_positions=tuple(tuple(pos) for pos in data.get("hard_positions", [])),
            extra_unbreakable=tuple(tuple(pos) for pos in data.get("extra_unbreakable", [])),
            exit_guard=int(data.get("exit_guard", 2)),
            enemy_spawns=tuple(data.get("enemy_spawns", [])),
            explosion_damage=int(data.get("explosion_damage", 20)),
        )


_LEVEL_DEFINITIONS_CACHE: list[LevelDefinition] | None = None


def _load_level_definitions() -> list[LevelDefinition]:
    """Level tanımlarını JSON dosyasından yükler"""
    global _LEVEL_DEFINITIONS_CACHE
    # Cache'i her zaman yeniden yükle (güncel veriler için)
    from repository.level_repository_json import LevelRepositoryJSON
    repo = LevelRepositoryJSON()
    _LEVEL_DEFINITIONS_CACHE = list(repo.find_all())
    return _LEVEL_DEFINITIONS_CACHE


class LevelRepository:
    """Basit level tanımlarını sağlayan repository."""

    @staticmethod
    def list_levels() -> Iterable[LevelConfig]:
        definitions = _load_level_definitions()
        configs: list[LevelConfig] = []
        for definition in definitions:
            # 1. Haritayı oluştur
            tiles = MapGenerator.generate_tiles(
                width=definition.width,
                height=definition.height,
                exit_position=definition.exit_position,
                breakable_positions=definition.breakable_positions,
                hard_positions=definition.hard_positions,
                extra_unbreakable=definition.extra_unbreakable,
            )
            
            # 2. Düşman pozisyonlarını doğrula ve düzelt (SOLID prensiplerine uygun, basit yaklaşım)
            tile_map = {(tile.x, tile.y): tile for tile in tiles}
            validated_enemy_positions = []
            
            # Tercih edilen pozisyonları doğrula
            for pos in definition.enemy_positions:
                x, y = pos
                # Harita sınırları içinde mi?
                if 0 <= x < definition.width and 0 <= y < definition.height:
                    tile = tile_map.get((x, y))
                    # Boş bir tile mı?
                    if tile and tile.type == TileType.EMPTY:
                        validated_enemy_positions.append(pos)
            
            # Eğer yeterli düşman pozisyonu yoksa, rastgele boş alanlardan ekle
            total_enemies = sum(spawn.get("count", 0) for spawn in definition.enemy_spawns)
            if len(validated_enemy_positions) < total_enemies:
                empty_positions = [
                    (tile.x, tile.y)
                    for tile in tiles
                    if tile.type == TileType.EMPTY and (tile.x, tile.y) not in validated_enemy_positions
                ]
                random.shuffle(empty_positions)
                needed = total_enemies - len(validated_enemy_positions)
                validated_enemy_positions.extend(empty_positions[:needed])
            
            # 3. Oyuncu başlangıç pozisyonunu doğrula
            player_start = definition.player_start
            x, y = player_start
            # Harita sınırları içinde mi ve boş bir tile mı?
            if not (0 <= x < definition.width and 0 <= y < definition.height):
                player_start = (1, 1)  # Varsayılan
            else:
                tile = tile_map.get((x, y))
                if not tile or tile.type != TileType.EMPTY or (x, y) in validated_enemy_positions:
                    # Geçerli bir pozisyon bul
                    for tile in tiles:
                        if tile.type == TileType.EMPTY and (tile.x, tile.y) not in validated_enemy_positions:
                            player_start = (tile.x, tile.y)
                            break
            
            configs.append(
                LevelConfig(
                    id=definition.id,
                    width=definition.width,
                    height=definition.height,
                    theme=definition.theme,
                    tiles=tiles,
                    player_start=player_start,
                    enemy_positions=validated_enemy_positions,
                    explosion_damage=definition.explosion_damage,
                    enemy_spawns=definition.enemy_spawns,
                )
            )
        return configs

    @staticmethod
    def find(level_id: str) -> LevelConfig | None:
        return next(
            (level for level in LevelRepository.list_levels() if level.id == level_id),
            None,
        )
