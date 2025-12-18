"""
Game Start Service: Oyun başlatma logic'i
Single Responsibility: Oyun başlatma ve PostgreSQL update
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from models.room import GameRoom
from services.game_setup_service import GameSetupService
from repository.room_repository import RoomRepository

logger = logging.getLogger(__name__)


class GameStartService:
    """Oyun başlatma logic'i için helper service."""
    
    def __init__(self, setup_service: GameSetupService, repository: RoomRepository):
        """
        Args:
            setup_service: Game setup service (level, enemy, player positioning)
            repository: Room repository (PostgreSQL update için)
        """
        self.setup_service = setup_service
        self.repository = repository
    
    def start_game(self, room: GameRoom) -> Optional[dict[str, Any]]:
        """
        Oyunu başlat.
        
        Args:
            room: Oyun odası
            
        Returns:
            Game started event dict veya None
        """
        if not room.is_full():
            return None
        
        # 1. Level yükle
        if not self.setup_service.load_level(room):
            return None  # Level yüklenemezse oyun başlatılamaz
        
        # 2. Oyunu başlat
        room.started = True
        logger.info(f"Game started in room {room.room_id}")
        
        # 3. Düşmanları spawn et
        self.setup_service.spawn_enemies(room)
        
        # 4. Oyunculara başlangıç pozisyonlarını ver
        self.setup_service.position_players(room)
        
        # 5. PostgreSQL'e güncelle (sadece started flag'i)
        self._update_room_started_flag(room)
        
        return {
            "type": "game_started",
            "level_id": room.level_id,
            "players": [p.to_dict() for p in room.players]
        }
    
    def _update_room_started_flag(self, room: GameRoom) -> None:
        """
        PostgreSQL'de oda started flag'ini güncelle.
        
        Args:
            room: Oyun odası
        """
        try:
            # Sadece started flag'ini güncelle, oyuncu pozisyonlarını değil
            with self.repository._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE rooms
                        SET started = %s
                        WHERE room_id = %s
                    """, (True, room.room_id))
                    conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update room started flag: {e}")

