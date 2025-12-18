"""
Enemy Damage Service: Düşman hasar verme logic'i
Single Responsibility: Düşman-oyuncu collision ve hasar verme yönetimi
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from models.room import Enemy, Player

logger = logging.getLogger(__name__)


@dataclass
class CollisionState:
    """Oyuncu-düşman collision durumu."""
    duration: float = 0.0  # Çarpışma süresi (saniye)
    cooldown: float = 0.0  # Hasar cooldown'u (saniye)
    last_enemy_id: Optional[str] = None  # Son çarpıştığı düşman ID'si


class EnemyDamageService:
    """
    Düşman hasar verme service'i - Single player mantığı ile uyumlu.
    
    Düşman oyuncuya doğru hareket etmeye çalıştığında (yakın olduğunda) hasar verir.
    """
    
    # Çarpışma ayarları (single player ile aynı)
    COLLISION_THRESHOLD = 3.0  # Sürekli hasar başlama süresi
    DAMAGE_COOLDOWN_INITIAL = 0.5  # İlk dokunuş cooldown (single player ile aynı)
    DAMAGE_COOLDOWN_CONTINUOUS = 0.2  # Sürekli hasar cooldown
    DAMAGE_AMOUNT = 10  # Hasar miktarı
    
    def __init__(self):
        """Service başlatır."""
        # Her oyuncu için collision state tutulur
        self._player_collision_states: dict[str, CollisionState] = {}
    
    def check_proximity(
        self,
        player_pos: tuple[int, int],
        enemy_pos: tuple[int, int],
        enemy_is_moving: bool = True,
    ) -> bool:
        """
        Oyuncu düşmana yakın mı? (yan yana veya aynı konum)
        
        Args:
            player_pos: Oyuncunun (x, y) koordinatı
            enemy_pos: Düşmanın (x, y) koordinatı
            enemy_is_moving: Düşman hareket ediyor mu? (False ise hasar yok)
            
        Returns:
            bool: Çarpışma var mı?
        """
        # Düşman hareket etmiyorsa çarpışma yok
        if not enemy_is_moving:
            return False
        
        dx = abs(enemy_pos[0] - player_pos[0])
        dy = abs(enemy_pos[1] - player_pos[1])
        # Manhattan distance <= 1 (aynı tile veya yan yana)
        return dx <= 1 and dy <= 1 and (dx + dy) <= 1
    
    def update_collision(
        self,
        player_id: str,
        delta: float,
        collision_detected: bool,
        enemy_id: Optional[str] = None,
    ) -> None:
        """
        Çarpışma durumunu günceller.
        
        Args:
            player_id: Oyuncu ID'si
            delta: Geçen zaman (saniye)
            collision_detected: Çarpışma var mı?
            enemy_id: Düşman ID'si (None ise çarpışma yok)
        """
        # Oyuncu için state yoksa oluştur
        if player_id not in self._player_collision_states:
            self._player_collision_states[player_id] = CollisionState()
        
        state = self._player_collision_states[player_id]
        state.cooldown = max(0.0, state.cooldown - delta)
        
        if collision_detected and enemy_id:
            same_enemy = enemy_id == state.last_enemy_id
            if same_enemy:
                # Aynı düşmanla devam → süresi artar
                state.duration += delta
            else:
                # Yeni düşman → süresi sıfırla
                state.duration = delta
            state.last_enemy_id = enemy_id
        else:
            # Çarpışma yok → sıfırla
            state.duration = 0.0
            state.last_enemy_id = None
    
    def should_apply_damage(self, player_id: str) -> bool:
        """
        Şu an hasar uygulanmalı mı?
        
        Args:
            player_id: Oyuncu ID'si
            
        Returns:
            bool: Hasar yapılsın mı?
        """
        if player_id not in self._player_collision_states:
            return False
        
        state = self._player_collision_states[player_id]
        if state.cooldown > 0:
            return False
        # Çarpışma süresi eşik değeri geçtiyse veya ilk dokunuş
        return state.duration > 0
    
    def reset_damage_cooldown(self, player_id: str) -> None:
        """
        Hasar cooldown'unu sıfırlar.
        
        Args:
            player_id: Oyuncu ID'si
        """
        if player_id not in self._player_collision_states:
            return
        
        state = self._player_collision_states[player_id]
        if state.duration >= self.COLLISION_THRESHOLD:
            # Sürekli hasar (daha sık)
            state.cooldown = self.DAMAGE_COOLDOWN_CONTINUOUS
        else:
            # İlk dokunuş (daha seyrek)
            state.cooldown = self.DAMAGE_COOLDOWN_INITIAL
    
    def apply_damage(self, player: Player) -> bool:
        """
        Oyuncuya hasar uygula.
        
        Args:
            player: Oyuncu
            
        Returns:
            bool: Hasar uygulandı mı?
        """
        if not self.should_apply_damage(player.player_id):
            return False
        
        old_health = player.health
        player.health = max(0, player.health - self.DAMAGE_AMOUNT)
        
        # KRİTİK: Hasar verdikten sonra duration'ı sıfırla ve cooldown set et
        # Böylece bir sonraki frame'de tekrar hasar verilmez
        if player.player_id in self._player_collision_states:
            state = self._player_collision_states[player.player_id]
            state.duration = 0.0  # Duration'ı sıfırla (tekrar hasar vermemek için)
            self.reset_damage_cooldown(player.player_id)  # Cooldown set et
        
        logger.info(
            f"👾 Enemy hit player {player.username} "
            f"(health: {old_health} -> {player.health})"
        )
        
        return True
    
    def check_and_apply_damage(
        self,
        player: Player,
        enemy: Enemy,
        enemy_was_moving: bool,
        delta: float,
    ) -> bool:
        """
        Düşman-oyuncu collision kontrolü ve hasar uygulama.
        
        Args:
            player: Oyuncu
            enemy: Düşman
            enemy_was_moving: Düşman hareket etti mi? (son hareketten beri)
            delta: Geçen zaman (saniye)
            
        Returns:
            bool: Hasar uygulandı mı?
        """
        # Proximity kontrolü
        collision_detected = self.check_proximity(
            player.position,
            enemy.position,
            enemy_is_moving=enemy_was_moving,
        )
        
        # Collision state'i güncelle
        self.update_collision(
            player.player_id,
            delta,
            collision_detected,
            enemy.enemy_id if collision_detected else None,
        )
        
        # Hasar uygula
        if collision_detected:
            return self.apply_damage(player)
        
        return False

