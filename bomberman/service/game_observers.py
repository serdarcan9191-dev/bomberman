"""
Game Event Observers: Concrete observer implementasyonları.
Bomba patlaması, düşman ölümü gibi eventleri dinler.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from service.game_event_service import GameEvent, GameEventType, GameObserver

if TYPE_CHECKING:
    from service.sound_service import SoundService

logger = logging.getLogger(__name__)


class SoundObserver(GameObserver):
    """Ses efektlerini yöneten observer."""
    
    def __init__(self, sound_service: 'SoundService') -> None:
        """
        Args:
            sound_service: Ses servisi
        """
        self._sound_service = sound_service
    
    def on_event(self, event: GameEvent) -> None:
        """Event geldiğinde ses efekti çal."""
        if event.event_type == GameEventType.BOMB_EXPLODED:
            self._sound_service.play_sound("explosion.wav")
        
        elif event.event_type == GameEventType.ENEMY_KILLED:
            self._sound_service.play_sound("enemy_death.wav")
        
        elif event.event_type == GameEventType.PLAYER_DAMAGED:
            self._sound_service.play_sound("enemy_attack.wav")
        
        elif event.event_type == GameEventType.POWERUP_COLLECTED:
            self._sound_service.play_sound("powerup.wav")
        
        elif event.event_type == GameEventType.WALL_DESTROYED:
            self._sound_service.play_sound("wall_break.wav")
        
        elif event.event_type == GameEventType.LEVEL_COMPLETED:
            self._sound_service.play_sound("level_complete.wav")


class ScoreObserver(GameObserver):
    """Skor takibi yapan observer."""
    
    def __init__(self) -> None:
        """Score tracker başlatır."""
        self.score: int = 0
        self.walls_destroyed: int = 0
        self.enemies_killed: int = 0
    
    def on_event(self, event: GameEvent) -> None:
        """Event geldiğinde skoru güncelle."""
        if event.event_type == GameEventType.BOMB_EXPLODED:
            # Bomba patladı
            logger.info("Bomb exploded!")
        
        elif event.event_type == GameEventType.ENEMY_KILLED:
            self.enemies_killed += 1
            self.score += 100
            logger.info(f"Enemy killed! Total: {self.enemies_killed}, Score: {self.score}")
        
        elif event.event_type == GameEventType.WALL_DESTROYED:
            wall_type = event.data.get("wall_type", "unknown")
            if wall_type == "breakable":
                self.walls_destroyed += 1
                self.score += 10
            elif wall_type == "hard":
                self.score += 20
            logger.info(f"Wall destroyed ({wall_type})! Score: {self.score}")
        
        elif event.event_type == GameEventType.POWERUP_COLLECTED:
            powerup_type = event.data.get("powerup_type", "unknown")
            self.score += 50
            logger.info(f"Powerup collected ({powerup_type})! Score: {self.score}")
        
        elif event.event_type == GameEventType.LEVEL_COMPLETED:
            self.score += 500
            logger.info(f"Level completed! Bonus: 500, Total Score: {self.score}")
    
    def reset(self) -> None:
        """Skoru sıfırla (yeni oyun için)."""
        self.score = 0
        self.walls_destroyed = 0
        self.enemies_killed = 0


class LoggerObserver(GameObserver):
    """Debug için tüm eventleri logla."""
    
    def on_event(self, event: GameEvent) -> None:
        """Event geldiğinde logla."""
        logger.debug(f"Game Event: {event.event_type.value}, Data: {event.data}")
