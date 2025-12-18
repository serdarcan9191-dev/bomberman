"""
Bomb Service: Bomba patlama ve update logic'i
Single Responsibility: Bomba timer, patlama, hasar verme
"""
from __future__ import annotations

import logging
from typing import Optional

from models.room import Bomb, GameRoom
from models.level import TileType

logger = logging.getLogger(__name__)


class BombService:
    """Bomba patlama ve update logic'i için helper service."""
    
    def __init__(self):
        """Bomb service başlat."""
        pass
    
    def update_bombs(self, room: GameRoom, delta: float) -> None:
        """
        Bombaları güncelle (timer, patlama).
        
        Args:
            room: Oyun odası
            delta: Geçen süre (saniye)
        """
        bombs_to_remove = []
        for bomb in room.bombs:
            if not bomb.exploded:
                bomb.timer -= delta
                if bomb.timer <= 0:
                    # Bomba patladı
                    logger.info(f"💣💣💣 BOMBA PATLADI at ({bomb.x}, {bomb.y}) - timer: {bomb.timer}")
                    bomb.exploded = True
                    bomb.explosion_timer = 1.0  # Patlama animasyonu süresi
                    # Patlama etkisini uygula (breakable wall'ları kır)
                    self.handle_bomb_explosion(room, bomb)
            else:
                # Patlama animasyonu için timer (1 saniye sonra kaldır)
                bomb.explosion_timer -= delta
                if bomb.explosion_timer <= 0:
                    bombs_to_remove.append(bomb)
        
        # Patlamış bombaları kaldır
        for bomb in bombs_to_remove:
            if bomb in room.bombs:
                room.bombs.remove(bomb)
    
    def handle_bomb_explosion(self, room: GameRoom, bomb: Bomb) -> None:
        """
        Bomba patlamasını işle - breakable wall'ları kır, oyunculara hasar ver.
        
        Args:
            room: Oyun odası
            bomb: Patlayan bomba
        """
        if not room.level_data:
            return
        
        # Bomba koyan oyuncunun bomb_power'ını al
        bomb_owner = room.get_player(bomb.player_id)
        radius = bomb_owner.bomb_power if bomb_owner else 1
        
        explosion_tiles = []
        
        # 4 yöne patlama
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        for dx, dy in directions:
            for r in range(1, radius + 1):  # radius kadar uzağa patlama
                tx, ty = bomb.x + dx * r, bomb.y + dy * r
                
                # Sınır kontrolü
                if tx < 0 or tx >= room.level_width or ty < 0 or ty >= room.level_height:
                    break
                
                tile_type = room.level_data.tile_at(tx, ty)
                
                # UNBREAKABLE duvarlar patlamayı durdurur
                if tile_type == TileType.UNBREAKABLE:
                    break
                
                # HARD duvarlar patlamayı durdurur (kırılmaz)
                if tile_type == TileType.HARD:
                    break
                
                # BREAKABLE duvarlar kırılır ve patlama durur
                if tile_type == TileType.BREAKABLE:
                    # Breakable wall'ı EMPTY'e çevir
                    room.level_data.tiles[(tx, ty)] = TileType.EMPTY
                    explosion_tiles.append((tx, ty))
                    logger.info(f"Breakable wall destroyed at ({tx}, {ty}) by bomb at ({bomb.x}, {bomb.y})")
                    break  # Patlama burada durur
                
                # EMPTY tile'lara patlama yayılır
                if tile_type == TileType.EMPTY:
                    explosion_tiles.append((tx, ty))
        
        # Merkez tile'ı ekle
        explosion_tiles.append((bomb.x, bomb.y))
        
        # Bomb model'ine explosion_tiles kaydet
        bomb.explosion_tiles = explosion_tiles
        
        # Oyunculara hasar ver (patlama tile'ında olan oyuncular hasar alır)
        # Player position tuple (x, y) formatında, explosion_tiles da tuple listesi
        for player in room.players:
            player_pos = player.position  # tuple[int, int]
            # Explosion tiles içinde mi kontrol et (tuple karşılaştırması)
            if player_pos in explosion_tiles:
                old_health = player.health
                player.health = max(0, player.health - 20)  # 20 hasar
                if player.health <= 0:
                    logger.info(f"💥 Player {player.username} KILLED by explosion at {player_pos} (was {old_health} HP)")
                else:
                    logger.info(f"💥 Player {player.username} took 20 damage from explosion at {player_pos}: {old_health} -> {player.health} HP")
            else:
                # Debug: Player pozisyonunu ve explosion tiles'ı logla (sadece yakınsa)
                # Sadece explosion tiles'a yakın oyuncuları logla (performans için)
                min_distance = min(abs(player_pos[0] - tx) + abs(player_pos[1] - ty) for tx, ty in explosion_tiles)
                if min_distance <= 2:  # 2 tile içindeyse logla
                    logger.debug(f"Player {player.username} at {player_pos} not in explosion tiles (distance: {min_distance}). Explosion tiles: {explosion_tiles[:10]}")
        
        logger.info(f"💣 Bomb exploded at ({bomb.x}, {bomb.y}) with radius {radius}, affected {len(explosion_tiles)} tiles")
        logger.info(f"   📍 Explosion tiles: {explosion_tiles}")
        logger.info(f"   👥 Players in room: {[(p.username, p.position, p.health) for p in room.players]}")

