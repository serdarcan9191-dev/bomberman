"""
Player Decorator Pattern: Power-up sistemini Decorator pattern ile implement eder.
SOLID Prensipleri:
- Single Responsibility: Her decorator tek bir power-up özelliğinden sorumlu
- Open/Closed: Yeni power-up eklemek için mevcut kodu değiştirmeye gerek yok
- Liskov Substitution: Tüm decorator'lar Player interface'ini implement eder
- Interface Segregation: Player interface sadece gerekli metodları içerir
- Dependency Inversion: Decorator'lar Player interface'ine bağımlı, somut sınıflara değil
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.bomberman import Bomberman


class PlayerInterface(ABC):
    """Player interface - Decorator pattern için base interface."""
    
    @abstractmethod
    def get_speed(self) -> float:
        """Oyuncunun hızını döndürür."""
        pass
    
    @abstractmethod
    def get_bomb_count(self) -> int:
        """Oyuncunun maksimum bomba sayısını döndürür."""
        pass
    
    @abstractmethod
    def get_bomb_power(self) -> int:
        """Oyuncunun bomba gücünü döndürür."""
        pass
    
    @abstractmethod
    def get_health(self) -> int:
        """Oyuncunun canını döndürür."""
        pass


class PlayerDecorator(PlayerInterface):
    """
    Decorator base class - Tüm decorator'ların temel sınıfı.
    Decorator Pattern: Runtime'da özellik eklemek için kullanılır.
    """
    
    def __init__(self, player: PlayerInterface) -> None:
        """
        Args:
            player: Decorate edilecek player (başka bir decorator veya base player)
        """
        self._player = player
    
    def get_speed(self) -> float:
        """Base player'ın hızını döndürür (decorator'lar override edebilir)."""
        return self._player.get_speed()
    
    def get_bomb_count(self) -> int:
        """Base player'ın bomba sayısını döndürür (decorator'lar override edebilir)."""
        return self._player.get_bomb_count()
    
    def get_bomb_power(self) -> int:
        """Base player'ın bomba gücünü döndürür (decorator'lar override edebilir)."""
        return self._player.get_bomb_power()
    
    def get_health(self) -> int:
        """Base player'ın canını döndürür (decorator'lar override edebilir)."""
        return self._player.get_health()


class BombermanAdapter(PlayerInterface):
    """
    Adapter Pattern: Bomberman model'ini PlayerInterface'e adapte eder.
    Bu sayede Bomberman'ı decorator pattern ile kullanabiliriz.
    """
    
    def __init__(self, bomberman: 'Bomberman') -> None:
        """
        Args:
            bomberman: Adapt edilecek Bomberman instance
        """
        self._bomberman = bomberman
    
    def get_speed(self) -> float:
        return self._bomberman.speed
    
    def get_bomb_count(self) -> int:
        return self._bomberman.bomb_count
    
    def get_bomb_power(self) -> int:
        return self._bomberman.bomb_power
    
    def get_health(self) -> int:
        return self._bomberman.health


class SpeedBoostDecorator(PlayerDecorator):
    """
    Speed Boost Decorator: Oyuncunun hızını artırır.
    Decorator Pattern: Runtime'da speed özelliği ekler.
    """
    
    SPEED_MULTIPLIER = 1.25
    
    def get_speed(self) -> float:
        """Base player'ın hızını %25 artırır."""
        return self._player.get_speed() * self.SPEED_MULTIPLIER


class BombCountBoostDecorator(PlayerDecorator):
    """
    Bomb Count Boost Decorator: Oyuncunun maksimum bomba sayısını artırır.
    Decorator Pattern: Runtime'da bomb_count özelliği ekler.
    """
    
    BOMB_COUNT_BOOST = 1
    
    def get_bomb_count(self) -> int:
        """Base player'ın bomba sayısını 1 artırır."""
        return self._player.get_bomb_count() + self.BOMB_COUNT_BOOST


class BombPowerBoostDecorator(PlayerDecorator):
    """
    Bomb Power Boost Decorator: Oyuncunun bomba gücünü artırır.
    Decorator Pattern: Runtime'da bomb_power özelliği ekler.
    """
    
    BOMB_POWER_BOOST = 1
    
    def get_bomb_power(self) -> int:
        """Base player'ın bomba gücünü 1 artırır."""
        return self._player.get_bomb_power() + self.BOMB_POWER_BOOST


class HealthBoostDecorator(PlayerDecorator):
    """
    Health Boost Decorator: Oyuncunun canını artırır.
    Decorator Pattern: Runtime'da health özelliği ekler.
    """
    
    HEALTH_BOOST = 20
    
    def get_health(self) -> int:
        """Base player'ın canını 20 artırır."""
        return self._player.get_health() + self.HEALTH_BOOST

