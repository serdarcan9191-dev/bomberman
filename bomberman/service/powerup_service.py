"""
Powerup Service: Power-up mekanikleri (spawn, effect, tracking).
"""
from __future__ import annotations

from enum import Enum
from typing import Optional


class PowerupType(Enum):
    """Power-up türleri."""
    SPEED = "speed"
    BOMB_COUNT = "bomb_count"
    BOMB_POWER = "bomb_power"
    HEALTH = "health"


class Powerup:
    """Tek bir power-up nesnesi."""

    def __init__(self, x: int, y: int, powerup_type: PowerupType) -> None:
        self.x = x
        self.y = y
        self.type = powerup_type
        self.collected = False

    def collect(self) -> None:
        """Power-up toplanmış işaretler."""
        self.collected = True


class PowerupService:
    """Power-up yönetimi."""

    def __init__(self) -> None:
        """Service başlatır."""
        self._powerups: list[Powerup] = []
        self._spawn_chance: float = 0.3  # %30 olasılık (0.0-1.0)

    def spawn_powerup(self, x: int, y: int, powerup_type: PowerupType) -> Powerup:
        """
        Power-up spawn eder.
        
        Args:
            x, y: Spawn konumu
            powerup_type: Powerup türü
            
        Returns:
            Powerup: Spawned powerup nesnesi
        """
        powerup = Powerup(x, y, powerup_type)
        self._powerups.append(powerup)
        return powerup

    def check_collection(self, player_pos: tuple[int, int]) -> list[PowerupType]:
        """
        Oyuncunun toplayabileceği power-up'ları kontrol eder.
        
        Args:
            player_pos: Oyuncunun pozisyonu
            
        Returns:
            list: Toplanan power-up türleri
        """
        collected = []
        for powerup in self._powerups:
            if not powerup.collected and (powerup.x, powerup.y) == player_pos:
                powerup.collect()
                collected.append(powerup.type)
        return collected

    def apply_powerup(self, powerup_type: PowerupType, player) -> 'PlayerInterface':
        """
        Oyuncuya power-up efektini Decorator Pattern ile uygular.
        
        Args:
            powerup_type: Power-up türü
            player: Oyuncu nesnesi (Bomberman veya PlayerInterface)
            
        Returns:
            PlayerInterface: Decorate edilmiş player (decorator chain)
        """
        from model.player_decorator import (
            BombermanAdapter,
            BombCountBoostDecorator,
            BombPowerBoostDecorator,
            HealthBoostDecorator,
            PlayerInterface,
            SpeedBoostDecorator
        )
        
        # Eğer player Bomberman ise, adapter ile wrap et
        if not isinstance(player, PlayerInterface):
            player = BombermanAdapter(player)
        
        # Decorator Pattern: Power-up tipine göre decorator ekle
        if powerup_type == PowerupType.SPEED:
            return SpeedBoostDecorator(player)
        elif powerup_type == PowerupType.BOMB_COUNT:
            return BombCountBoostDecorator(player)
        elif powerup_type == PowerupType.BOMB_POWER:
            return BombPowerBoostDecorator(player)
        elif powerup_type == PowerupType.HEALTH:
            return HealthBoostDecorator(player)
        else:
            return player

    def remove_powerup(self, powerup: Powerup) -> None:
        """Power-up'ı listeden kaldırır."""
        if powerup in self._powerups:
            self._powerups.remove(powerup)

    def get_all_powerups(self) -> list[Powerup]:
        """Tüm power-up'ları döndürür."""
        return self._powerups.copy()

    def get_active_powerups(self) -> list[Powerup]:
        """Toplanmamış power-up'ları döndürür."""
        return [p for p in self._powerups if not p.collected]

    def set_spawn_chance(self, chance: float) -> None:
        """
        Power-up spawn olasılığını ayarlar.
        
        Args:
            chance: Olasılık (0.0-1.0)
        """
        self._spawn_chance = max(0.0, min(1.0, chance))

    def get_spawn_chance(self) -> float:
        """Power-up spawn olasılığını döndürür."""
        return self._spawn_chance

    def clear(self) -> None:
        """Tüm power-up'ları temizler."""
        self._powerups.clear()
