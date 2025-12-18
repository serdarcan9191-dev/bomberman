"""
Game State Service: Oyun state serialization ve query
Single Responsibility: Game state'i dict formatına çevirme
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from models.room import GameRoom
from models.level import TileType

logger = logging.getLogger(__name__)


class GameStateService:
    """Oyun state serialization için helper service."""
    
    def __init__(self):
        """Game state service başlat."""
        pass
    
    def get_game_state(self, room: GameRoom) -> dict[str, Any]:
        """
        Oyun state'ini dict formatına çevir.
        
        Args:
            room: Oyun odası
            
        Returns:
            Game state dict
        """
        # Player dict'lerine player_id ekle
        players_data = []
        for p in room.players:
            player_dict = p.to_dict()
            player_dict["player_id"] = p.player_id  # player_id'yi ekle
            players_data.append(player_dict)
        
        # Bombaları dict formatına çevir
        bombs_data = []
        for bomb in room.bombs:
            bombs_data.append({
                "x": bomb.x,
                "y": bomb.y,
                "player_id": bomb.player_id,
                "timer": bomb.timer,
                "exploded": bomb.exploded,
                "explosion_timer": bomb.explosion_timer,
                "explosion_tiles": [{"x": tx, "y": ty} for tx, ty in bomb.explosion_tiles]  # Patlama tile'ları
            })
        
        # Kırılan breakable wall'ları gönder (original_breakable_walls set'inden)
        destroyed_walls = []
        if room.level_data and hasattr(room, 'original_breakable_walls'):
            # Orijinal breakable wall pozisyonlarını kontrol et
            for (x, y) in room.original_breakable_walls:
                # Şu anki level'da bu tile EMPTY ise, kırılmış demektir
                current_tile = room.level_data.tiles.get((x, y), TileType.EMPTY)
                if current_tile == TileType.EMPTY:
                    destroyed_walls.append({"x": x, "y": y})
        
        # Debug: destroyed_walls logla (sadece varsa)
        if destroyed_walls:
            logger.info(f"🧱 Sending {len(destroyed_walls)} destroyed walls to clients: {destroyed_walls}")
        
        # Düşmanları dict formatına çevir (Server-authoritative)
        enemies_data = []
        for enemy in room.enemies:
            enemies_data.append(enemy.to_dict())
        
        return {
            "type": "game_state",
            "level_id": room.level_id,  # Level ID'yi gönder (level geçişi için)
            "players": players_data,
            "bombs": bombs_data,
            "destroyed_walls": destroyed_walls,  # Kırılan duvarlar
            "enemies": enemies_data  # Düşmanlar (Server-authoritative)
        }

