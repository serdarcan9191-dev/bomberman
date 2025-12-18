"""
Game Event Handlers: Oyun içi event'ler (hareket, bomba, vb.)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from models.room import GameRoom
from services.game_setup_service import GameSetupService
from services.game_movement_service import GameMovementService
from services.game_state_service import GameStateService
from services.game_query_service import GameQueryService
from services.game_update_service import GameUpdateService
from services.game_start_service import GameStartService
from repository.room_repository import RoomRepository

logger = logging.getLogger(__name__)


class GameHandlers:
    """Oyun içi event handler'ları."""
    
    def __init__(self, rooms: dict[str, GameRoom]):
        """
        Args:
            rooms: room_id -> GameRoom mapping (in-memory cache)
        """
        self.rooms = rooms
        self.repository = RoomRepository()  # PostgreSQL repository
        
        # Helper services
        self.setup_service = GameSetupService()  # Game setup helper
        self.movement_service = GameMovementService()  # Game movement and collision helper
        self.state_service = GameStateService()  # Game state serialization
        self.query_service = GameQueryService(rooms)  # Room/player query
        self.start_service = GameStartService(self.setup_service, self.repository)  # Game start logic
        self.update_service = GameUpdateService(self.movement_service, self.state_service, self.setup_service)  # Game loop update
    
    def handle_player_move(self, socket_id: str, direction: str) -> Optional[dict[str, Any]]:
        """
        Oyuncu hareket - Server authoritative with full collision detection.
        
        Args:
            socket_id: Socket.io session ID
            direction: "up", "down", "left", "right"
            
        Returns:
            Game state dict veya None
        """
        room, player = self.query_service.get_player_by_socket(socket_id)
        if not room or not player:
            return None
        
        # Game Movement Service kullanarak hareket et
        new_pos = self.movement_service.move_player(room, player, direction)
        
        if new_pos is None:
            # Hareket edilemedi - collision var
            return self.state_service.get_game_state(room)
        
        return self.state_service.get_game_state(room)
    
    def handle_place_bomb(self, socket_id: str) -> Optional[dict[str, Any]]:
        """
        Oyuncu bomba koydu.
        
        Args:
            socket_id: Socket.io session ID
            
        Returns:
            Game state dict veya None
        """
        room, player = self.query_service.get_player_by_socket(socket_id)
        if not room or not player:
            return None
        
        # Game Movement Service kullanarak bomba koy
        new_bomb = self.movement_service.place_bomb(room, player)
        
        if new_bomb is None:
            # Bomba koyulamadı (zaten bomba var)
            return self.state_service.get_game_state(room)
        
        return self.state_service.get_game_state(room)
    
    def start_game(self, room_id: str) -> Optional[dict[str, Any]]:
        """
        Oyunu başlat.
        
        Args:
            room_id: Oda ID'si
            
        Returns:
            Game started event dict
        """
        room = self.query_service.get_room(room_id)
        if not room:
            return None
        
        # Game Start Service kullanarak oyunu başlat
        return self.start_service.start_game(room)
    
    def get_game_state(self, room_id: str) -> Optional[dict[str, Any]]:
        """
        Oyun state'ini al.
        
        Args:
            room_id: Oda ID'si
            
        Returns:
            Game state dict
        """
        room = self.query_service.get_room(room_id)
        if not room:
            return None
        
        return self.state_service.get_game_state(room)
    
    def find_player_room(self, socket_id: str) -> Optional[GameRoom]:
        """Socket ID'ye göre oyuncunun bulunduğu odayı bul."""
        return self.query_service.find_player_room(socket_id)
    
    def update_game(self, room_id: str, delta: float) -> Optional[dict[str, Any]]:
        """
        Oyun state'ini güncelle (bombalar, patlamalar, vb.)
        
        Args:
            room_id: Oda ID'si
            delta: Geçen süre (saniye)
            
        Returns:
            Game state dict veya None
        """
        room = self.query_service.get_room(room_id)
        if not room:
            return None
        
        # Game Update Service kullanarak oyunu güncelle
        return self.update_service.update_game(room, delta)
    

