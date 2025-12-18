"""
Game Update Service: Oyun loop update logic'i
Single Responsibility: Game loop içinde bombalar, düşmanlar güncelleme
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from models.room import GameRoom
from services.level_service import get_level
from services.bomb_service import BombService
from services.game_movement_service import GameMovementService
from services.game_state_service import GameStateService
from services.game_level_service import GameLevelService

logger = logging.getLogger(__name__)


class GameUpdateService:
    """Oyun loop update logic'i için helper service."""
    
    def __init__(self, movement_service: GameMovementService, state_service: GameStateService, setup_service):
        """
        Args:
            movement_service: Game movement service (düşman güncelleme için)
            state_service: Game state service (state serialization için)
            setup_service: Game setup service (level geçiş için)
        """
        self.movement_service = movement_service
        self.state_service = state_service
        self.bomb_service = BombService()
        self.level_service = GameLevelService(setup_service)
    
    def update_game(self, room: GameRoom, delta: float) -> Optional[dict[str, Any]]:
        """
        Oyun state'ini güncelle (bombalar, patlamalar, düşmanlar).
        
        Args:
            room: Oyun odası
            delta: Geçen süre (saniye)
            
        Returns:
            Game state dict veya None
        """
        if not room.started:
            return None
        
        # Level bilgisi yoksa yükle
        if not room.level_data:
            level_data = get_level(room.level_id)
            if level_data:
                room.level_data = level_data
                room.level_width = level_data.width
                room.level_height = level_data.height
            else:
                return None
        
        # Bombaları güncelle
        self.bomb_service.update_bombs(room, delta)
        
        # Düşmanları güncelle (Server-authoritative)
        self.movement_service.update_enemies(room, delta)
        
        # Game over kontrolü: Tüm oyuncular öldü mü?
        alive_players = [p for p in room.players if p.health > 0]
        game_over = len(alive_players) == 0
        
        # Level tamamlama kontrolü (sadece canlı oyuncular varsa)
        level_advanced = False
        if not game_over and self.level_service.check_level_completion(room):
            # Tüm oyuncular exit'e ulaştı, bir sonraki level'e geç
            if self.level_service.advance_to_next_level(room):
                logger.info(f"🎮 Level advanced to {room.level_id} in room {room.room_id}")
                level_advanced = True
            else:
                logger.info(f"🏆 Game completed in room {room.room_id}")
        
        # Game state'i serialize et ve döndür
        game_state = self.state_service.get_game_state(room)
        
        # Game over flag'i ekle
        if game_over:
            game_state["game_over"] = True
            logger.info(f"💀 Game over: All players died in room {room.room_id}")
        
        # Level geçişi varsa, bunu game state'e ekle
        if level_advanced:
            game_state["level_advanced"] = True
            game_state["new_level_id"] = room.level_id
        
        return game_state

