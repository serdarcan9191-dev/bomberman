"""
Level Repository: Level verilerini JSON dosyasından yükleyen repository.
SOLID - Repository Pattern: Veri erişim katmanını soyutlar.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from model.level import LevelDefinition, Theme


class LevelRepositoryJSON:
    """
    Level Repository: JSON dosyasından level verilerini yönetir.
    Repository Pattern - Veri erişim mantığını iş mantığından ayırır.
    """

    def __init__(self, json_path: str | None = None) -> None:
        """
        Args:
            json_path: JSON dosyasının yolu (None ise varsayılan data/levels.json)
        """
        if json_path is None:
            # Proje root'una göre data/levels.json
            json_path = Path(__file__).parent.parent / "data" / "levels.json"
        
        self._json_path = Path(json_path)
        self._cache: dict[str, LevelDefinition] | None = None

    def find_by_id(self, level_id: str) -> Optional[LevelDefinition]:
        """ID'ye göre level bulur"""
        definitions = self._load_all()
        return definitions.get(level_id)

    def find_all(self) -> Iterable[LevelDefinition]:
        """Tüm levelları getirir (sıralı)"""
        definitions = self._load_all()
        # ID'ye göre sıralı döndür (level_1, level_2, ...)
        for key in sorted(definitions.keys(), key=lambda x: self._extract_level_number(x)):
            yield definitions[key]

    def save(self, definition: LevelDefinition) -> None:
        """Level kaydeder (JSON dosyasını günceller)"""
        definitions = self._load_all()
        definitions[definition.id] = definition
        
        # JSON dosyasına yaz
        data = []
        for key in sorted(definitions.keys(), key=lambda x: self._extract_level_number(x)):
            defn = definitions[key]
            data.append({
                "id": defn.id,
                "width": defn.width,
                "height": defn.height,
                "theme": defn.theme.value,
                "player_start": list(defn.player_start),
                "exit_position": list(defn.exit_position),
                "enemy_spawns": [dict(spawn) for spawn in defn.enemy_spawns],
                "exit_guard": defn.exit_guard,
                "explosion_damage": defn.explosion_damage,
            })
        
        self._json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Cache'i temizle
        self._cache = None

    def delete(self, level_id: str) -> bool:
        """Level siler"""
        definitions = self._load_all()
        if level_id not in definitions:
            return False
        
        del definitions[level_id]
        
        # JSON dosyasına yaz
        data = []
        for key in sorted(definitions.keys(), key=lambda x: self._extract_level_number(x)):
            defn = definitions[key]
            data.append({
                "id": defn.id,
                "width": defn.width,
                "height": defn.height,
                "theme": defn.theme.value,
                "player_start": list(defn.player_start),
                "exit_position": list(defn.exit_position),
                "enemy_spawns": [dict(spawn) for spawn in defn.enemy_spawns],
                "exit_guard": defn.exit_guard,
                "explosion_damage": defn.explosion_damage,
            })
        
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Cache'i temizle
        self._cache = None
        return True

    def _load_all(self) -> dict[str, LevelDefinition]:
        """Tüm levelları JSON dosyasından yükler (cache'lenmiş)"""
        if self._cache is not None:
            return self._cache

        definitions: dict[str, LevelDefinition] = {}
        
        if not self._json_path.exists():
            return definitions
        
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data:
                    defn = self._map_dict_to_definition(item)
                    definitions[defn.id] = defn
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  JSON dosyası yüklenemedi: {e}")
        
        self._cache = definitions
        return definitions

    def _map_dict_to_definition(self, data: dict) -> LevelDefinition:
        """JSON dict'ini LevelDefinition'a dönüştürür"""
        from service.map_generator import MapGenerator
        
        # Temel bilgiler
        level_id = data["id"]
        width = int(data.get("width", 11))
        height = int(data.get("height", 9))
        player_start = tuple(data.get("player_start", [1, 1]))
        exit_position = tuple(data.get("exit_position", [9, 7]))
        enemy_spawns = tuple(data.get("enemy_spawns", []))
        
        # Düşman sayısı
        enemy_count = sum(spawn.get("count", 0) for spawn in enemy_spawns)
        
        # Level numarası çıkar
        try:
            level_number = int(level_id.split("_")[-1])
        except (ValueError, IndexError):
            level_number = 1
        
        # JSON'da breakable_positions ve hard_positions varsa kullan, yoksa generate et
        breakable_positions_json = data.get("breakable_positions", [])
        hard_positions_json = data.get("hard_positions", [])
        
        if breakable_positions_json and hard_positions_json:
            # JSON'dan pozisyonları kullan (multiplayer için tutarlılık)
            breakable_positions = tuple(tuple(pos) for pos in breakable_positions_json)
            hard_positions = tuple(tuple(pos) for pos in hard_positions_json)
            
            # Enemy pozisyonlarını generate et (JSON'da yok)
            positions = MapGenerator.generate_positions(
                level_id=level_id,
                width=width,
                height=height,
                enemy_count=enemy_count,
                level_number=level_number,
                player_start=player_start,
            )
        else:
            # Eski yöntem: Tüm pozisyonları generate et
            positions = MapGenerator.generate_positions(
                level_id=level_id,
                width=width,
                height=height,
                enemy_count=enemy_count,
                level_number=level_number,
                player_start=player_start,
            )
            breakable_positions = tuple(positions.get("breakable", []))
            hard_positions = tuple(positions.get("hard", []))
        
        return LevelDefinition(
            id=level_id,
            width=width,
            height=height,
            theme=Theme(data.get("theme", "city").lower()),
            player_start=player_start,
            enemy_positions=tuple(positions.get("enemy", [])),
            exit_position=exit_position,
            breakable_positions=breakable_positions,
            hard_positions=hard_positions,
            extra_unbreakable=tuple(positions.get("extra_unbreakable", [])),
            exit_guard=int(data.get("exit_guard", 2)),
            enemy_spawns=enemy_spawns,
            explosion_damage=int(data.get("explosion_damage", 20)),
        )

    @staticmethod
    def _extract_level_number(level_id: str) -> int:
        """level_X formatından X numarasını çıkarır"""
        try:
            return int(level_id.split("_")[-1])
        except (ValueError, IndexError):
            return 999


