"""
Room Event Handlers: Oda oluşturma ve katılma işlemleri
PostgreSQL repository kullanarak oda yönetimi
"""
from __future__ import annotations

import logging
import random
import string
import uuid
from typing import Any, Optional

from models.room import GameRoom, Player
from repository.room_repository import RoomRepository

logger = logging.getLogger(__name__)


def generate_room_code() -> str:
    """6 haneli benzersiz oda kodu oluştur."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


class RoomHandlers:
    """Oda yönetimi event handler'ları - PostgreSQL kullanır."""
    
    def __init__(self, rooms: dict[str, GameRoom], room_codes: dict[str, str]):
        """
        Args:
            rooms: room_id -> GameRoom mapping (in-memory cache)
            room_codes: room_code -> room_id mapping (in-memory cache)
        """
        self.rooms = rooms  # In-memory cache
        self.room_codes = room_codes  # In-memory cache
        self.repository = RoomRepository()  # PostgreSQL repository
    
    def handle_create_room(self, socket_id: str, username: str) -> dict[str, Any]:
        """
        Yeni oda oluştur - PostgreSQL'e kaydet.
        
        Args:
            socket_id: Socket.io session ID
            username: Oyuncu adı
            
        Returns:
            Response dict
        """
        # Önce oyuncunun zaten bir odada olup olmadığını kontrol et
        existing_room = self.find_player_room_by_socket(socket_id)
        if existing_room:
            return {
                "type": "error",
                "message": "Zaten bir odadasınız. Önce odadan çıkmalısınız."
            }
        
        # PostgreSQL'den de kontrol et
        try:
            active_rooms = self.repository.list_active_rooms()
            for room in active_rooms:
                if room.get_player_by_socket(socket_id):
                    return {
                        "type": "error",
                        "message": "Zaten bir odadasınız. Önce odadan çıkmalısınız."
                    }
        except Exception as e:
            logger.warning(f"Failed to check existing rooms from PostgreSQL: {e}")
        
        # Yeni oda oluştur
        room_id = str(uuid.uuid4())
        room_code = generate_room_code()
        
        # Benzersiz oda kodu garantisi (PostgreSQL'den kontrol et)
        while self.repository.room_code_exists(room_code):
            room_code = generate_room_code()
        
        # Level bilgilerini ayarla (default level_1)
        room = GameRoom(
            room_id=room_id, 
            room_code=room_code,
            level_id="level_1",
            level_width=11,  # level_1 default width (gerçek değer)
            level_height=9   # level_1 default height (gerçek değer)
        )
        
        # Oluşturan oyuncuyu ekle
        player = Player(
            player_id=str(uuid.uuid4()),
            username=username,
            socket_id=socket_id,
            health=100  # Başlangıç canı 100
        )
        room.add_player(player)
        
        logger.info(f"Creating room {room_code} with player {username} (player_id: {player.player_id})")
        logger.info(f"Room has {len(room.players)} players before save")
        
        # PostgreSQL'e kaydet
        if not self.repository.create_room(room):
            logger.error(f"Failed to create room {room_code} in database")
            return {
                "type": "error",
                "message": "Oda oluşturulamadı"
            }
        
        logger.info(f"Room {room_code} successfully saved to database")
        
        # In-memory cache'e ekle
        self.rooms[room_id] = room
        self.room_codes[room_code] = room_id
        
        logger.info(f"Player {username} created room {room_code} ({room_id})")
        
        return {
            "type": "room_created",
            "room_code": room_code,
            "room_id": room_id,
            "player_id": player.player_id,
            "player_count": 1
        }
    
    def handle_join_room(self, socket_id: str, username: str, room_code: str) -> dict[str, Any]:
        """
        Oyuncu odaya katıl - PostgreSQL'den oku.
        
        Args:
            socket_id: Socket.io session ID
            username: Oyuncu adı
            room_code: Oda kodu
            
        Returns:
            Response dict veya None (hata durumunda)
        """
        room_code = room_code.strip().upper()
        
        # Önce oyuncunun zaten bir odada olup olmadığını kontrol et
        existing_room = self.find_player_room_by_socket(socket_id)
        if existing_room:
            return {
                "type": "error",
                "message": "Zaten bir odadasınız. Önce odadan çıkmalısınız."
            }
        
        # PostgreSQL'den odayı bul
        room = self.repository.get_room_by_code(room_code)
        
        if not room:
            return {
                "type": "error",
                "message": "Geçersiz oda kodu"
            }
        
        if room.is_full():
            return {
                "type": "error",
                "message": "Oda dolu"
            }
        
        if room.started:
            return {
                "type": "error",
                "message": "Oyun zaten başlamış"
            }
        
        # Oyuncuyu odaya ekle
        player = Player(
            player_id=str(uuid.uuid4()),
            username=username,
            socket_id=socket_id,
            health=100  # Başlangıç canı 100
        )
        room.add_player(player)
        
        # PostgreSQL'e kaydet
        if not self.repository.add_player_to_room(room.room_id, player):
            return {
                "type": "error",
                "message": "Odaya katılamadı"
            }
        
        # In-memory cache'i güncelle
        self.rooms[room.room_id] = room
        self.room_codes[room_code] = room.room_id
        
        logger.info(f"Player {username} joined room {room_code}")
        
        # Başarılı katılım response'u
        return {
            "type": "player_joined",
            "player_id": player.player_id,
            "username": username,
            "room_code": room_code,
            "player_count": len(room.players)
        }
    
    def handle_leave_room(self, socket_id: str) -> Optional[dict[str, Any]]:
        """
        Oyuncu odadan çıkar - PostgreSQL'den sil.
        
        Args:
            socket_id: Socket.io session ID
            
        Returns:
            Response dict veya None (room_id ve room_code içerir)
        """
        # Önce in-memory cache'den bul
        room = self.find_player_room_by_socket(socket_id)
        if not room:
            # PostgreSQL'den bul
            # Socket ID'ye göre odayı bulmak için tüm aktif odaları kontrol et
            active_rooms = self.repository.list_active_rooms()
            for r in active_rooms:
                if r.get_player_by_socket(socket_id):
                    room = r
                    break
        
        if not room:
            return None
        
        player = room.get_player_by_socket(socket_id)
        if not player:
            return None
        
        # İlk oyuncu (odayı oluşturan) mu?
        is_room_creator = len(room.players) > 0 and room.players[0].socket_id == socket_id
        
        # PostgreSQL'den oyuncuyu çıkar
        self.repository.remove_player_from_room(room.room_id, player.player_id)
        
        # In-memory'den oyuncuyu çıkar
        room.remove_player(player.player_id)
        
        logger.info(f"Player {player.username} left room {room.room_id}")
        
        # Eğer odayı oluşturan oyuncu çıktıysa veya oda boşsa, odayı tamamen sil
        if is_room_creator or len(room.players) == 0:
            self.repository.delete_room(room.room_id)
            if room.room_id in self.rooms:
                del self.rooms[room.room_id]
            if room.room_code in self.room_codes:
                del self.room_codes[room.room_code]
            logger.info(f"Room {room.room_code} deleted (creator left or empty)")
        else:
            # Odayı güncelle (sadece oyuncu sayısı değişti)
            try:
                # Sadece oyuncu sayısını güncellemek için update_room kullan
                self.repository.update_room(room)
            except Exception as e:
                logger.warning(f"Failed to update room after player left: {e}")
        
        return {
            "type": "player_left",
            "player_id": player.player_id,
            "room_id": room.room_id,
            "room_code": room.room_code,
            "player_count": len(room.players),
            "room_deleted": is_room_creator or len(room.players) == 0
        }
    
    def find_player_room_by_socket(self, socket_id: str) -> Optional[GameRoom]:
        """Socket ID'ye göre oyuncunun bulunduğu odayı bul."""
        for room in self.rooms.values():
            if room.get_player_by_socket(socket_id):
                return room
        return None
    
    def get_room_by_socket(self, socket_id: str) -> Optional[GameRoom]:
        """Socket ID'ye göre odayı bul."""
        return self.find_player_room_by_socket(socket_id)

