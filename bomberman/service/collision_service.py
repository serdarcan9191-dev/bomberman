"""
Collision Service: Çarpışma hesaplamaları ve çarpışma yönetimi.
Pure logic; side-effect'siz çarpışma algılaması ve hasar hesaplaması.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class CollisionState:
    """Çarpışma durumunu tutan state."""
    duration: float = 0.0  # Mevcut çarpışmanın süresi (saniye)
    cooldown: float = 0.0  # Hasar cooldown'u
    same_enemy: bool = False  # Aynı düşmanla mı çarpışıyoruz?


class CollisionService:
    """Çarpışma hesaplamaları ve yönetimi."""

    # Çarpışma ayarları (saniye)
    COLLISION_THRESHOLD = 3.0  # Sürekli hasar başlama süresi
    DAMAGE_COOLDOWN_INITIAL = 0.5  # İlk dokunuş cooldown
    DAMAGE_COOLDOWN_CONTINUOUS = 0.2  # Sürekli hasar cooldown

    def __init__(self) -> None:
        """Service başlatır."""
        self._collision_state = CollisionState()

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
        delta: float,
        collision_detected: bool,
        same_enemy: bool = False,
    ) -> None:
        """
        Çarpışma durumunu günceller.
        
        Args:
            delta: Geçen zaman (saniye)
            collision_detected: Çarpışma var mı?
            same_enemy: Aynı düşmanla mı çarpışıyoruz?
        """
        self._collision_state.cooldown -= delta

        if collision_detected:
            if same_enemy:
                # Aynı düşmanla devam → süresi artar
                self._collision_state.duration += delta
                self._collision_state.same_enemy = True
            else:
                # Yeni düşman → süresi sıfırla
                self._collision_state.duration = delta
                self._collision_state.same_enemy = False
        else:
            # Çarpışma yok → sıfırla
            self._collision_state.duration = 0.0
            self._collision_state.same_enemy = False
            self._collision_state.cooldown = 0.0

    def should_apply_damage(self) -> bool:
        """
        Şu an hasar uygulanmalı mı?
        
        Returns:
            bool: Hasar yapılsın mı?
        """
        if self._collision_state.cooldown > 0:
            return False
        # Çarpışma süresi eşik değeri geçtiyse veya ilk dokunuş
        return self._collision_state.duration > 0

    def reset_damage_cooldown(self) -> None:
        """Hasar cooldown'unu sıfırlar."""
        if self._collision_state.duration >= self.COLLISION_THRESHOLD:
            # Sürekli hasar (daha sık)
            self._collision_state.cooldown = self.DAMAGE_COOLDOWN_CONTINUOUS
        else:
            # İlk dokunuş (daha seyrek)
            self._collision_state.cooldown = self.DAMAGE_COOLDOWN_INITIAL

    def get_collision_duration(self) -> float:
        """Mevcut çarpışmanın süresini döndürür (saniye)."""
        return self._collision_state.duration

    def is_continuous_damage(self) -> bool:
        """Sürekli hasar aşamasında mıyız?"""
        return self._collision_state.duration >= self.COLLISION_THRESHOLD

    def reset(self) -> None:
        """Tüm çarpışma state'ini sıfırlar."""
        self._collision_state = CollisionState()
