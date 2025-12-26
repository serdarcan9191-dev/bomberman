"""
Game Event Service: Observer Pattern implementasyonu.
Oyun eventlerini (bomba patlaması, düşman ölümü, power-up) yönetir.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class GameEventType(Enum):
    """Oyun event tipleri."""
    BOMB_PLACED = "bomb_placed"
    BOMB_EXPLODED = "bomb_exploded"
    ENEMY_KILLED = "enemy_killed"
    PLAYER_DAMAGED = "player_damaged"
    PLAYER_DIED = "player_died"
    POWERUP_COLLECTED = "powerup_collected"
    WALL_DESTROYED = "wall_destroyed"
    LEVEL_COMPLETED = "level_completed"


@dataclass
class GameEvent:
    """Oyun event verisi."""
    event_type: GameEventType
    data: dict[str, Any]


class GameObserver(ABC):
    """Observer base class - event'leri dinler."""
    
    @abstractmethod
    def on_event(self, event: GameEvent) -> None:
        """Event geldiğinde çağrılır."""
        pass


class GameEventService:  #gözlemlenen 
    """
    Subject (Gözlemlenen) - Observer Pattern.
    Event'leri yönetir ve observer'ları bilgilendirir.
    """
    
    def __init__(self) -> None:
        """Service başlatır."""
        self._observers: list[GameObserver] = []
        self._event_listeners: dict[GameEventType, list[Callable[[GameEvent], None]]] = {}
    
    def attach(self, observer: GameObserver) -> None:
        """Observer ekle (tüm event'leri dinler)."""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def detach(self, observer: GameObserver) -> None:
        """Observer çıkar."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def add_listener(self, event_type: GameEventType, callback: Callable[[GameEvent], None]) -> None:
        """Belirli bir event tipine callback ekle."""
        if event_type not in self._event_listeners:
            self._event_listeners[event_type] = []
        self._event_listeners[event_type].append(callback)
    
    def notify(self, event: GameEvent) -> None:
        """Tüm observer'ları bilgilendir."""
        # Observer'ları bilgilendir
        for observer in self._observers:
            observer.on_event(event)
        
        # Event-specific callback'leri çağır
        if event.event_type in self._event_listeners:
            for callback in self._event_listeners[event.event_type]:
                callback(event)
    
    def emit(self, event_type: GameEventType, **data) -> None:
        """Event yayınla (kısayol metod)."""
        event = GameEvent(event_type=event_type, data=data)
        self.notify(event)
