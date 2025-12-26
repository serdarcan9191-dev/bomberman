"""
Enemy tanımları - Strategy Pattern kullanarak farklı düşman davranışları.
Base class: Enemy
Alt sınıflar: StaticEnemy, ChasingEnemy, SmartEnemy

SOLID Prensipleri:
- Single Responsibility: Her enemy sınıfı kendi hareket stratejisinden sorumlu
- Open/Closed: Yeni enemy tipleri eklemek için mevcut kodu değiştirmeye gerek yok
- Liskov Substitution: Tüm enemy alt sınıfları Enemy base class'ını değiştirmeden kullanılabilir
- Interface Segregation: Enemy base class sadece gerekli metodları içerir
- Dependency Inversion: tile_provider callback kullanılarak bağımlılık tersine çevrildi
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Callable, Tuple

from model.level import TileType


class EnemyType(Enum):
    """Düşman tipleri"""
    STATIC = auto()
    CHASING = auto()
    SMART = auto()


class Enemy(ABC):
    """
    Base Enemy sınıfı - Tüm düşmanların ortak özelliklerini içerir.
    Strategy Pattern: Her alt sınıf farklı hareket stratejisi uygular.
    """
    def __init__(
        self,
        position: Tuple[int, int],
        health: int,
        max_health: int,
        enemy_type: EnemyType,
        move_interval: float = 0.5
    ) -> None:
        self.position = position
        self.health = health
        self.max_health = max_health
        self.enemy_type = enemy_type
        self.move_interval = move_interval

    def movement_interval(self) -> float:
        """Hareket aralığını döndürür"""
        return self.move_interval

    def is_alive(self) -> bool:
        """Düşman canlı mı?"""
        return self.health > 0

    def take_damage(self, amount: int) -> None:
        """Hasar alır"""
        self.health = max(0, self.health - amount)
    
    def health_percentage(self) -> float:
        """Can yüzdesini döndürür (0.0 - 1.0)"""
        if self.max_health == 0:
            return 0.0
        return max(0.0, min(1.0, self.health / self.max_health))

    @abstractmethod
    def update(
        self,
        player_pos: Tuple[int, int] | None,
        tile_provider: Callable[[int, int], TileType],
    ) -> None:
        """
        Düşmanın hareket mantığını günceller.
        Her alt sınıf kendi stratejisini uygular.
        """
        pass


class StaticEnemy(Enemy):
    """
    Statik Düşman: Doğduğu yerden sadece 1 birim uzaklığa hareket edebilir.
    Rastgele yönlerde sınırlı hareket.
    """
    MAX_HEALTH = 20
    
    def __init__(self, position: Tuple[int, int]) -> None:
        super().__init__(
            position=position, 
            health=self.MAX_HEALTH, 
            max_health=self.MAX_HEALTH,
            enemy_type=EnemyType.STATIC, 
            move_interval=1.6
        )
        self._spawn_position: Tuple[int, int] = position

    def update(
        self,
        player_pos: Tuple[int, int] | None,
        tile_provider: Callable[[int, int], TileType],
    ) -> None:
        """Doğduğu yerden sadece 1 birim uzaklığa hareket edebilir"""
        old_pos = self.position
        
        # Rastgele bir yöne hareket et (doğduğu yerden max 1 birim uzakta)
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(directions)
        
        for dx, dy in directions:
            new_x = self.position[0] + dx
            new_y = self.position[1] + dy
            
            # Doğduğu yerden uzaklık kontrolü (Manhattan distance)
            distance = abs(new_x - self._spawn_position[0]) + abs(new_y - self._spawn_position[1])
            if distance > 1:
                continue
            
            # MovementService ile hareket kontrolü
            from service.movement_service import MovementService
            if MovementService.can_move_to(new_x, new_y, tile_provider):
                self.position = (new_x, new_y)
                break
        
        # Debug: Hareket kontrolü
        if old_pos == self.position:
            # Hareket edemediyse, spawn pozisyonuna dön
            if self.position != self._spawn_position:
                from service.movement_service import MovementService
                if MovementService.can_move_to(self._spawn_position[0], self._spawn_position[1], tile_provider):
                    self.position = self._spawn_position


class ChasingEnemy(Enemy):
    """
    Takip Eden Düşman: Doğduğu satır veya sütun boyunca hareket eder.
    Bomberman'a doğru yaklaşmaya çalışır ama sadece kendi satır/sütunu boyunca.
    """
    MAX_HEALTH = 30
    
    def __init__(self, position: Tuple[int, int]) -> None:
        super().__init__(
            position=position, 
            health=self.MAX_HEALTH, 
            max_health=self.MAX_HEALTH,
            enemy_type=EnemyType.CHASING, 
            move_interval=0.8  # Daha hızlı hareket
        )
        self._spawn_position: Tuple[int, int] = position
        # Hareket yönü: True = yatay (doğduğu satır boyunca), False = dikey (doğduğu sütun boyunca)
        self._move_horizontal: bool = random.choice([True, False])
        # Hareket yönü: 1 = sağ/aşağı, -1 = sol/yukarı
        self._direction: int = random.choice([1, -1])
        self._stuck_attempts: int = 0  # Takılma sayacı

    def update(
        self,
        player_pos: Tuple[int, int] | None,
        tile_provider: Callable[[int, int], TileType],
    ) -> None:
        """Doğduğu satır veya sütun boyunca gidip gelir (basit ping-pong hareketi)"""
        from service.movement_service import MovementService
        
        old_pos = self.position
        
        # Yatay hareket: Doğduğu satır (y koordinatı sabit) boyunca hareket eder
        if self._move_horizontal:
            # Y koordinatı spawn pozisyonu ile aynı olmalı
            if self.position[1] != self._spawn_position[1]:
                self.position = (self.position[0], self._spawn_position[1])
                return
            
            # Mevcut yönde hareket et
            target = (self.position[0] + self._direction, self._spawn_position[1])
        else:
            # Dikey hareket: Doğduğu sütun (x koordinatı sabit) boyunca hareket eder
            if self.position[0] != self._spawn_position[0]:
                self.position = (self._spawn_position[0], self.position[1])
                return
            
            # Mevcut yönde hareket et
            target = (self._spawn_position[0], self.position[1] + self._direction)
        
        # Hareket edebilir miyiz kontrol et
        if MovementService.can_move_to(target[0], target[1], tile_provider):
            self.position = target
            self._stuck_attempts = 0  # Hareket etti, sayacı sıfırla
        else:
            # Engel var - yön değiştir ve hemen dene
            self._direction *= -1
            
            if self._move_horizontal:
                target = (self.position[0] + self._direction, self._spawn_position[1])
            else:
                target = (self._spawn_position[0], self.position[1] + self._direction)
            
            if MovementService.can_move_to(target[0], target[1], tile_provider):
                self.position = target
                self._stuck_attempts = 0
            else:
                # Her iki yön de tıkalı - takıldık!
                self._stuck_attempts += 1
                
                # 2 kere takılınca eksen değiştir (yatay→dikey veya dikey→yatay)
                if self._stuck_attempts >= 2:
                    self._move_horizontal = not self._move_horizontal
                    self._direction = random.choice([1, -1])  # Yeni eksende rastgele yön
                    self._stuck_attempts = 0


class SmartEnemy(Enemy):
    """
    Akıllı Düşman: Bomberman'a doğru en kısa yolu bulmaya çalışır.
    Sadece 4 yönlü hareket eder, daha esnek hareket stratejisi.
    """
    MAX_HEALTH = 40
    
    def __init__(self, position: Tuple[int, int]) -> None:
        super().__init__(
            position=position, 
            health=self.MAX_HEALTH, 
            max_health=self.MAX_HEALTH,
            enemy_type=EnemyType.SMART, 
            move_interval=2.0  # Daha hızlı hareket
        )

    def update(
        self,
        player_pos: Tuple[int, int] | None,
        tile_provider: Callable[[int, int], TileType],
    ) -> None:
        """Bomberman'a doğru en kısa yolu bulmaya çalışır (sadece 4 yönlü hareket: kuzey, güney, doğu, batı)"""
        if player_pos is None:
            return
        
        from service.movement_service import MovementService
        
        dx = player_pos[0] - self.position[0]
        dy = player_pos[1] - self.position[1]
        
        if dx == 0 and dy == 0:
            return
        
        # Sadece 4 yönlü hareket: (0,1)=Güney, (0,-1)=Kuzey, (1,0)=Doğu, (-1,0)=Batı
        # Öncelik: Hangisi daha uzaksa o yönde hareket et
        candidates = []
        
        if abs(dx) > abs(dy):
            # Yatay hareket öncelikli
            if dx > 0:
                candidates.append((1, 0))  # Doğu
            elif dx < 0:
                candidates.append((-1, 0))  # Batı
            
            if dy > 0:
                candidates.append((0, 1))  # Güney
            elif dy < 0:
                candidates.append((0, -1))  # Kuzey
        else:
            # Dikey hareket öncelikli
            if dy > 0:
                candidates.append((0, 1))  # Güney
            elif dy < 0:
                candidates.append((0, -1))  # Kuzey
            
            if dx > 0:
                candidates.append((1, 0))  # Doğu
            elif dx < 0:
                candidates.append((-1, 0))  # Batı
        
        # İlk geçerli hareketi uygula
        for delta in candidates:
            new_x = self.position[0] + delta[0]
            new_y = self.position[1] + delta[1]
            
            if MovementService.can_move_to(new_x, new_y, tile_provider):
                self.position = (new_x, new_y)
                break
