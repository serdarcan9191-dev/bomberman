"""
Game Query Service: Room ve player lookup işlemleri
Single Responsibility: Room/player bulma logic'i
"""
from __future__ import annotations

import logging
from typing import Optional

from models.room import GameRoom, Player

logger = logging.getLogger(__name__)


class GameQueryService:
    """Room ve player query işlemleri için helper service."""
    
    def __init__(self, rooms: dict[str, GameRoom]):
        """
        Args:
            rooms: room_id -> GameRoom mapping (in-memory cache)
        """
        self.rooms = rooms
    
    def find_player_room(self, socket_id: str) -> Optional[GameRoom]:
        """
        Socket ID'ye göre oyuncunun bulunduğu odayı bul.
        
        Args:
            socket_id: Socket.io session ID
            
        Returns:
            GameRoom veya None
        """
        for room in self.rooms.values():
            if room.get_player_by_socket(socket_id):
                return room
        return None
    
    def get_room(self, room_id: str) -> Optional[GameRoom]:
        """
        Room ID'ye göre odayı bul.
        
        Args:
            room_id: Oda ID'si
            
        Returns:
            GameRoom veya None
        """
        return self.rooms.get(room_id)
    
    def get_player_by_socket(self, socket_id: str) -> tuple[Optional[GameRoom], Optional[Player]]:
        """
        Socket ID'ye göre oyuncuyu ve odasını bul.
        
        Args:
            socket_id: Socket.io session ID
            
        Returns:
            (GameRoom, Player) tuple veya (None, None)
        """
        room = self.find_player_room(socket_id)
        if not room:
            return (None, None)
        
        player = room.get_player_by_socket(socket_id)
        if not player:
            return (None, None)
        
        return (room, player)

