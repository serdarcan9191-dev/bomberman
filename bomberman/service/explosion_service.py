"""
Explosion Service: Patlama hesaplamaları ve hasar yönetimi.
Bombaların patlama yarıçapını, etkilenen tile'ları ve hasar dağılımını yönetir.
"""
from __future__ import annotations

from typing import Callable


class ExplosionService:
    """Patlama mekanikleri."""

    def __init__(self, default_damage: int = 20) -> None:
        """
        Service başlatır.
        
        Args:
            default_damage: Varsayılan patlama hasarı
        """
        self._default_damage = default_damage

    def calculate_explosion_tiles(
        self,
        bomb_x: int,
        bomb_y: int,
        radius: int,
        tile_checker: Callable[[int, int], bool],  # True = geçilemez (duvar vb)
    ) -> list[tuple[int, int]]:
        """
        Patlama tarafından etkilenen tile'ları hesaplar.
        
        Args:
            bomb_x, bomb_y: Bombanın koordinatları
            radius: Patlama yarıçapı (1 birim = tile)
            tile_checker: Tile geçilebilir mi kontrol eden callback (True = geçilemez)
            
        Returns:
            list: Etkilenen tile'ların [(x, y), ...] listesi
        """
        affected: list[tuple[int, int]] = []
        affected.append((bomb_x, bomb_y))  # Bombanın kendisi

        # 4 yönde (kuzey, güney, doğu, batı) patlama yayılması
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            for step in range(1, radius + 1):
                tx, ty = bomb_x + dx * step, bomb_y + dy * step
                # Duvar ile karşılaştıysa dur
                if tile_checker(tx, ty):
                    break
                affected.append((tx, ty))

        return affected

    def apply_damage_to_targets(
        self,
        affected_tiles: list[tuple[int, int]],
        player_pos: tuple[int, int],
        player_take_damage: Callable[[int], None],
        player_is_alive: Callable[[], bool],
        enemies: list,  # Enemy nesneleri
        damage: int | None = None,
    ) -> bool:
        """
        Patlama hasarını oyuncu ve düşmanlara uygular.
        
        Args:
            affected_tiles: Etkilenen tile listesi
            player_pos: Oyuncunun pozisyonu
            player_take_damage: Oyuncuya hasar uygulayan callback
            player_is_alive: Oyuncu canlı mı kontrol eden callback
            enemies: Düşman listesi
            damage: Hasar miktarı (None = default)
            
        Returns:
            bool: Oyuncu öldü mü?
        """
        damage = damage or self._default_damage

        # Oyuncu hasarı
        if player_pos in affected_tiles:
            player_take_damage(damage)
            if not player_is_alive():
                return True  # Oyuncu öldü

        # Düşman hasarı
        for enemy in enemies:
            if hasattr(enemy, "position") and hasattr(enemy, "is_alive") and hasattr(enemy, "take_damage"):
                if enemy.position in affected_tiles and enemy.is_alive():
                    enemy.take_damage(damage)

        return False

    def get_default_damage(self) -> int:
        """Varsayılan patlama hasarını döndürür."""
        return self._default_damage

    def set_default_damage(self, damage: int) -> None:
        """Varsayılan patlama hasarını ayarlar."""
        self._default_damage = max(1, damage)
