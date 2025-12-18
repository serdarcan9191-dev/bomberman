"""
Game Room Models: Oda ve oyuncu modelleri
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional

from models.level import LevelData


@dataclass
class Player:
    """Oyuncu verisi."""
    player_id: str
    username: str
    socket_id: str  # Socket.io session ID
    position: tuple[int, int] = (1, 1)
    health: int = 100
    ready: bool = False
    bomb_power: int = 1  # Bomba patlama radius'u
    bomb_count: int = 1  # Maksimum aynı anda koyulabilecek bomba sayısı
    reached_exit: bool = False  # Exit'e ulaştı mı?
    
    def to_dict(self) -> dict:
        """Oyuncu verisini dict'e çevir."""
        return {
            "player_id": self.player_id,
            "username": self.username,
            "position": list(self.position),
            "health": self.health,
            "ready": self.ready,
            "bomb_power": self.bomb_power,
            "bomb_count": self.bomb_count,
            "reached_exit": self.reached_exit
        }


@dataclass
class Bomb:
    """Bomba verisi."""
    x: int
    y: int
    player_id: str  # Bomba koyan oyuncu
    timer: float = 4.0  # Patlama süresi (saniye)
    exploded: bool = False
    explosion_timer: float = 1.0  # Patlama animasyonu süresi (saniye)
    explosion_tiles: list[tuple[int, int]] = field(default_factory=list)  # Patlama etkisi olan tile'lar


@dataclass
class Enemy:
    """Düşman verisi - Server-authoritative."""
    enemy_id: str
    enemy_type: str  # "static", "chasing", "smart"
    position: tuple[int, int]
    spawn_position: tuple[int, int] = None  # Doğduğu pozisyon (static enemy için)
    health: int = 100
    alive: bool = True
    last_move_time: float = 0.0  # Son hareket zamanı (timer için)
    
    def __post_init__(self):
        """spawn_position yoksa position'a eşitle."""
        if self.spawn_position is None:
            self.spawn_position = self.position
    
    def to_dict(self) -> dict:
        """Düşman verisini dict'e çevir."""
        return {
            "enemy_id": self.enemy_id,
            "enemy_type": self.enemy_type,
            "position": list(self.position),
            "health": self.health,
            "alive": self.alive
        }


@dataclass
class GameRoom:
    """Oyun odası - 2 oyuncu."""
    room_id: str
    room_code: str  # Paylaşılabilir 6 haneli kod
    players: list[Player] = field(default_factory=list)
    started: bool = False
    level_id: str = "level_1"
    level_width: int = 11  # Default level_1 width (gerçek değer)
    level_height: int = 9  # Default level_1 height (gerçek değer)
    level_data: Optional[LevelData] = None  # Level tile bilgileri
    bombs: list[Bomb] = field(default_factory=list)  # Aktif bombalar
    enemies: list[Enemy] = field(default_factory=list)  # Düşmanlar (Server-authoritative)
    original_breakable_walls: set[tuple[int, int]] = field(default_factory=set)  # Orijinal breakable wall pozisyonları
    
    def is_full(self) -> bool:
        """Oda dolu mu?"""
        return len(self.players) >= 2
    
    def add_player(self, player: Player) -> bool:
        """Oyuncu ekle."""
        if self.is_full():
            return False
        self.players.append(player)
        return True
    
    def remove_player(self, player_id: str) -> Optional[Player]:
        """Oyuncu çıkar."""
        for i, player in enumerate(self.players):
            if player.player_id == player_id:
                return self.players.pop(i)
        return None
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Oyuncu bul."""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None
    
    def get_player_by_socket(self, socket_id: str) -> Optional[Player]:
        """Socket ID'ye göre oyuncu bul."""
        for player in self.players:
            if player.socket_id == socket_id:
                return player
        return None

