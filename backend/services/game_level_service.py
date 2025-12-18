"""
Game Level Service: Level geçiş ve yönetim logic'i
Single Responsibility: Level tamamlama ve geçiş işlemleri
"""
from __future__ import annotations

import logging
from typing import Optional

from models.room import GameRoom
from services.game_setup_service import GameSetupService

logger = logging.getLogger(__name__)


class GameLevelService:
    """Level geçiş ve yönetim logic'i için helper service."""
    
    def __init__(self, setup_service: GameSetupService):
        """
        Args:
            setup_service: Game setup service (level yükleme, spawn, positioning için)
        """
        self.setup_service = setup_service
    
    def check_level_completion(self, room: GameRoom) -> bool:
        """
        Tüm oyuncular exit'e ulaştı mı kontrol et.
        
        Args:
            room: Oyun odası
            
        Returns:
            bool: Tüm oyuncular exit'e ulaştı mı?
        """
        if not room.started:
            return False
        
        # Canlı oyuncuları say (health > 0)
        alive_players = [p for p in room.players if p.health > 0]
        
        if len(alive_players) == 0:
            return False  # Hiç canlı oyuncu yok
        
        # Tüm canlı oyuncular exit'e ulaştı mı?
        all_reached_exit = all(p.reached_exit for p in alive_players)
        
        if all_reached_exit:
            logger.info(f"🎉 All {len(alive_players)} players reached exit in room {room.room_id}")
        
        return all_reached_exit
    
    def get_next_level_id(self, current_level_id: str) -> Optional[str]:
        """
        Bir sonraki level ID'sini hesapla.
        
        Args:
            current_level_id: Mevcut level ID (örn: "level_1")
            
        Returns:
            Bir sonraki level ID veya None (max level'a ulaşıldıysa)
        """
        try:
            # "level_1" -> 1
            level_number = int(current_level_id.split("_")[-1])
            next_level_number = level_number + 1
            
            # Maksimum 10 level var
            if next_level_number > 10:
                return None  # Oyun bitti
            
            return f"level_{next_level_number}"
        except (ValueError, IndexError):
            logger.error(f"Invalid level_id format: {current_level_id}")
            return None
    
    def advance_to_next_level(self, room: GameRoom) -> bool:
        """
        Bir sonraki level'e geç.
        
        Args:
            room: Oyun odası
            
        Returns:
            bool: Başarılı mı?
        """
        next_level_id = self.get_next_level_id(room.level_id)
        if not next_level_id:
            logger.info(f"🏆 Game completed! Max level reached in room {room.room_id}")
            return False  # Oyun bitti
        
        logger.info(f"📈 Advancing from {room.level_id} to {next_level_id} in room {room.room_id}")
        
        # Level ID'yi güncelle
        room.level_id = next_level_id
        
        # Level'i yükle
        if not self.setup_service.load_level(room):
            logger.error(f"Failed to load next level {next_level_id}")
            return False
        
        # Oyuncuları resetle (yeni level için)
        for player in room.players:
            player.reached_exit = False
            # Ölen oyuncuları yeniden canlandır (yeni level'da 100 can ile başla)
            player.health = 100
            logger.info(f"🔄 Player {player.username} reset for new level: health=100, reached_exit=False")
        
        # Bombaları temizle
        room.bombs.clear()
        
        # Düşmanları yeniden spawn et
        self.setup_service.spawn_enemies(room)
        
        # Oyuncuları yeni pozisyonlara yerleştir
        self.setup_service.position_players(room)
        
        logger.info(f"✅ Advanced to {next_level_id}, players repositioned and revived")
        
        return True

