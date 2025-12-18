"""
Game Movement Service: Oyun içi hareket, collision detection, fizik
Single Responsibility: Tüm hareket ve collision logic'i
"""
from __future__ import annotations

import logging
import random
from typing import Optional

from models.room import Bomb, Enemy, GameRoom, Player
from models.level import TileType
from services.enemy_damage_service import EnemyDamageService

logger = logging.getLogger(__name__)


class GameMovementService:
    """Oyun içi hareket ve collision detection için helper service."""
    
    def __init__(self):
        """Game movement service başlat."""
        self.enemy_damage_service = EnemyDamageService()
    
    def can_player_move_to(
        self,
        room: GameRoom,
        player: Player,
        new_x: int,
        new_y: int
    ) -> tuple[bool, str]:
        """
        Oyuncunun belirtilen pozisyona hareket edip edemeyeceğini kontrol et.
        
        Args:
            room: Oyun odası
            player: Oyuncu
            new_x: Yeni X pozisyonu
            new_y: Yeni Y pozisyonu
            
        Returns:
            (can_move: bool, reason: str)
        """
        # Level bilgisi yüklenmiş olmalı (setup sırasında yüklenir)
        if not room.level_data:
            return (False, "level_not_loaded")
        
        # 1. Sınır kontrolü
        if new_x < 0 or new_x >= room.level_width or new_y < 0 or new_y >= room.level_height:
            return (False, "out_of_bounds")
        
        # 2. Tile collision kontrolü - BREAKABLE, HARD, UNBREAKABLE engellenir
        if not room.level_data.can_move_to(new_x, new_y):
            return (False, "tile_collision")
        
        # 3. Bomba collision kontrolü - bomba olan tile'lara girilemez
        for bomb in room.bombs:
            if bomb.x == new_x and bomb.y == new_y and not bomb.exploded:
                return (False, "bomb_collision")
        
        # 4. Oyuncular arası collision kontrolü (sadece canlı ve exit'e ulaşmamış oyuncular)
        for other_player in room.players:
            if other_player.player_id != player.player_id:
                # Ölü oyuncular ve exit'e ulaşan oyuncular collision'da yer almaz
                if (other_player.health > 0 and 
                    not other_player.reached_exit and 
                    other_player.position == (new_x, new_y)):
                    return (False, "player_collision")
        
        # 5. Düşman collision kontrolü - düşmanların üzerine geçilemez
        for enemy in room.enemies:
            if enemy.alive and enemy.position == (new_x, new_y):
                return (False, "enemy_collision")
        
        return (True, "ok")
    
    def move_player(
        self,
        room: GameRoom,
        player: Player,
        direction: str
    ) -> Optional[tuple[int, int]]:
        """
        Oyuncuyu hareket ettir (collision kontrolü ile).
        
        Args:
            room: Oyun odası
            player: Oyuncu
            direction: "up", "down", "left", "right"
            
        Returns:
            Yeni pozisyon (x, y) veya None (hareket edilemezse)
        """
        x, y = player.position
        new_x, new_y = x, y
        
        if direction == "up":
            new_y = y - 1
        elif direction == "down":
            new_y = y + 1
        elif direction == "left":
            new_x = x - 1
        elif direction == "right":
            new_x = x + 1
        else:
            return None
        
        # Collision kontrolü
        can_move, reason = self.can_player_move_to(room, player, new_x, new_y)
        if not can_move:
            logger.debug(f"Player {player.username} move blocked: {reason} at ({new_x}, {new_y})")
            return None
        
        # Hareket geçerli - pozisyonu güncelle
        player.position = (new_x, new_y)
        logger.info(f"✅ Player {player.username} moved {direction}: ({x}, {y}) -> ({new_x}, {new_y})")
        
        # Exit tile kontrolü
        if room.level_data:
            tile_type = room.level_data.tile_at(new_x, new_y)
            if tile_type == TileType.EXIT and not player.reached_exit:
                player.reached_exit = True
                logger.info(f"🎯 Player {player.username} reached exit at ({new_x}, {new_y})")
        
        return (new_x, new_y)
    
    def can_place_bomb(
        self,
        room: GameRoom,
        player: Player
    ) -> bool:
        """
        Oyuncunun bomba koyup koyamayacağını kontrol et.
        
        Args:
            room: Oyun odası
            player: Oyuncu
            
        Returns:
            bool: Bomba koyulabilir mi?
        """
        bomb_x, bomb_y = player.position
        
        # Aynı pozisyonda zaten bomba var mı kontrol et
        for bomb in room.bombs:
            if bomb.x == bomb_x and bomb.y == bomb_y and not bomb.exploded:
                return False
        
        return True
    
    def place_bomb(
        self,
        room: GameRoom,
        player: Player
    ) -> Optional[Bomb]:
        """
        Oyuncu için bomba yerleştir.
        
        Args:
            room: Oyun odası
            player: Oyuncu
            
        Returns:
            Bomb objesi veya None (koyulamazsa)
        """
        if not self.can_place_bomb(room, player):
            return None
        
        bomb_x, bomb_y = player.position
        new_bomb = Bomb(
            x=bomb_x,
            y=bomb_y,
            player_id=player.player_id,
            timer=4.0,
            exploded=False,
            explosion_timer=1.0
        )
        room.bombs.append(new_bomb)
        
        # Aktif bomba sayısını hesapla (log için)
        active_bombs = sum(1 for b in room.bombs if not b.exploded and b.player_id == player.player_id)
        logger.info(f"Player {player.username} placed bomb at ({bomb_x}, {bomb_y}) (active: {active_bombs})")
        
        return new_bomb
    
    def can_enemy_move_to(
        self,
        room: GameRoom,
        enemy: Enemy,
        new_x: int,
        new_y: int
    ) -> bool:
        """
        Düşmanın belirtilen pozisyona hareket edip edemeyeceğini kontrol et.
        
        Args:
            room: Oyun odası
            enemy: Düşman
            new_x: Yeni X pozisyonu
            new_y: Yeni Y pozisyonu
            
        Returns:
            bool: Hareket edilebilir mi?
        """
        if not room.level_data:
            return False
        
        # 1. Tile collision kontrolü
        if not room.level_data.can_move_to(new_x, new_y):
            return False
        
        # 2. Oyuncu pozisyonu kontrolü - düşmanlar oyuncuların üzerine geçemez (sadece canlı ve exit'e ulaşmamış oyuncular)
        for player in room.players:
            if (player.health > 0 and 
                not player.reached_exit and 
                player.position == (new_x, new_y)):
                return False
        
        # 3. Bomba kontrolü
        for bomb in room.bombs:
            if bomb.x == new_x and bomb.y == new_y and not bomb.exploded:
                return False
        
        # 4. Diğer düşmanlar kontrolü
        for other_enemy in room.enemies:
            if other_enemy != enemy and other_enemy.alive and other_enemy.position == (new_x, new_y):
                return False
        
        return True
    
    def calculate_enemy_move(
        self,
        room: GameRoom,
        enemy: Enemy,
        nearest_player: Optional[Player]
    ) -> Optional[tuple[int, int]]:
        """
        Düşman için bir sonraki pozisyonu hesapla.
        
        Args:
            room: Oyun odası
            enemy: Düşman
            nearest_player: En yakın oyuncu (None ise static enemy gibi davranır)
            
        Returns:
            Yeni pozisyon (x, y) veya None (hareket edilemezse)
        """
        if not room.level_data:
            return None
        
        new_pos = None
        
        if enemy.enemy_type == "static":
            # Static: Doğduğu yerden sadece 1 birim uzaklığa hareket et (single player mantığı)
            directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(directions)
            for dx, dy in directions:
                nx, ny = enemy.position[0] + dx, enemy.position[1] + dy
                
                # Doğduğu yerden uzaklık kontrolü (Manhattan distance)
                spawn_x, spawn_y = enemy.spawn_position
                distance = abs(nx - spawn_x) + abs(ny - spawn_y)
                if distance > 1:
                    continue  # Doğduğu yerden 1 birimden fazla uzak olamaz
                
                if self.can_enemy_move_to(room, enemy, nx, ny):
                    new_pos = (nx, ny)
                    break
            
            # Eğer hareket edemediyse ve spawn pozisyonunda değilse, spawn pozisyonuna dön
            if new_pos is None and enemy.position != enemy.spawn_position:
                if self.can_enemy_move_to(room, enemy, enemy.spawn_position[0], enemy.spawn_position[1]):
                    new_pos = enemy.spawn_position
        elif enemy.enemy_type == "chasing":
            # Chasing: En yakın oyuncuya doğru hareket et (basit yaklaşma)
            if not nearest_player:
                return None
            
            ex, ey = enemy.position
            tx, ty = nearest_player.position
            
            # Hedefe doğru en yakın geçerli tile'a git
            candidates = [
                (ex + 1, ey),  # Sağ
                (ex - 1, ey),  # Sol
                (ex, ey + 1),  # Alt
                (ex, ey - 1),  # Üst
            ]
            
            # En yakın adayı seç
            best_pos = None
            min_dist = float('inf')
            
            for nx, ny in candidates:
                if not self.can_enemy_move_to(room, enemy, nx, ny):
                    continue
                
                # En yakın pozisyonu seç
                dist = abs(nx - tx) + abs(ny - ty)
                if dist < min_dist:
                    min_dist = dist
                    best_pos = (nx, ny)
            
            new_pos = best_pos
        elif enemy.enemy_type == "smart":
            # Smart: Single player mantığı - Öncelikli yönde hareket et
            if not nearest_player:
                return None
            
            ex, ey = enemy.position
            tx, ty = nearest_player.position
            
            dx = tx - ex
            dy = ty - ey
            
            if dx == 0 and dy == 0:
                return None  # Zaten hedefte
            
            # Single player mantığı: Hangisi daha uzaksa o yönde öncelik ver
            candidates = []
            
            if abs(dx) > abs(dy):
                # Yatay hareket öncelikli
                if dx > 0:
                    candidates.append((ex + 1, ey))  # Doğu
                elif dx < 0:
                    candidates.append((ex - 1, ey))  # Batı
                
                if dy > 0:
                    candidates.append((ex, ey + 1))  # Güney
                elif dy < 0:
                    candidates.append((ex, ey - 1))  # Kuzey
            else:
                # Dikey hareket öncelikli
                if dy > 0:
                    candidates.append((ex, ey + 1))  # Güney
                elif dy < 0:
                    candidates.append((ex, ey - 1))  # Kuzey
                
                if dx > 0:
                    candidates.append((ex + 1, ey))  # Doğu
                elif dx < 0:
                    candidates.append((ex - 1, ey))  # Batı
            
            # İlk geçerli hareketi uygula (single player mantığı)
            for nx, ny in candidates:
                if self.can_enemy_move_to(room, enemy, nx, ny):
                    new_pos = (nx, ny)
                    break
        
        return new_pos
    
    def update_enemies(self, room: GameRoom, delta: float) -> None:
        """
        Düşmanları güncelle - Server-authoritative.
        Single player mantığı ile uyumlu: Düşman oyuncuya doğru hareket etmeye çalıştığında hasar verir.
        
        Args:
            room: Oyun odası
            delta: Geçen süre (saniye)
        """
        if not room.level_data:
            return
        
        # Düşman pozisyonlarını kaydet (hareket kontrolü için - single player mantığı)
        enemy_previous_positions: dict[str, tuple[int, int]] = {}
        for enemy in room.enemies:
            if enemy.alive:
                enemy_previous_positions[enemy.enemy_id] = enemy.position
        
        for enemy in room.enemies:
            if not enemy.alive:
                continue
            
            # En yakın oyuncuyu bul (tüm collision ve hareket için kullanılacak)
            nearest_player = None
            min_distance = float('inf')
            for player in room.players:
                # Sadece canlı ve exit'e ulaşmamış oyuncular
                if player.health > 0 and not player.reached_exit:
                    dist = abs(player.position[0] - enemy.position[0]) + abs(player.position[1] - enemy.position[1])
                    if dist < min_distance:
                        min_distance = dist
                        nearest_player = player
            
            # Düşman-bomba collision kontrolü (explosion tiles)
            for bomb in room.bombs:
                if bomb.exploded and enemy.position in bomb.explosion_tiles:
                    old_health = enemy.health
                    enemy.health = max(0, enemy.health - 50)
                    if enemy.health <= 0:
                        enemy.alive = False
                        logger.info(f"💥 Enemy {enemy.enemy_id} killed by bomb at {enemy.position}, health: {old_health} -> 0")
                    else:
                        logger.info(f"💥 Enemy {enemy.enemy_id} took damage from bomb at {enemy.position}, health: {old_health} -> {enemy.health}")
            
            # Düşman hareketi (basit AI)
            enemy.last_move_time += delta
            move_interval = 0.5  # 0.5 saniyede bir hareket
            
            if enemy.last_move_time >= move_interval:
                # Düşman hareketi hesapla
                # KRİTİK: Static enemy'ler için nearest_player=None gönder (rastgele hareket)
                # Chasing/Smart enemy'ler için nearest_player gönder (oyuncuya doğru)
                target_player = None if enemy.enemy_type == "static" else nearest_player
                new_pos = self.calculate_enemy_move(room, enemy, target_player)
                
                # Pozisyonu güncelle
                if new_pos:
                    enemy.position = new_pos
                    enemy.last_move_time = 0.0
            
            # Düşman-oyuncu collision kontrolü ve hasar verme
            # KRİTİK: Tüm yakın oyunculara hasar ver (sadece en yakın oyuncuya değil)
            # Single player mantığı: Tüm düşmanlar (static dahil) hasar verir
            # - Static enemy: Rastgele hareket eder, oyuncu konumunu bilmez, ama yaklaşırsa hasar verir
            # - Chasing/Smart enemy: Oyuncuya doğru hareket eder, yaklaşırsa hasar verir
            
            # Düşman pozisyonu değiştiyse hareket etti
            previous_pos = enemy_previous_positions.get(enemy.enemy_id, enemy.position)
            enemy_is_moving = (previous_pos != enemy.position)
            
            # Tüm canlı oyuncuları kontrol et (sadece en yakın oyuncuya değil)
            for player in room.players:
                # Sadece canlı ve exit'e ulaşmamış oyuncular
                if player.health > 0 and not player.reached_exit:
                    # Tüm enemy type'lar için collision kontrolü (static dahil)
                    self.enemy_damage_service.check_and_apply_damage(
                        player,
                        enemy,
                        enemy_is_moving,
                        delta,
                    )

