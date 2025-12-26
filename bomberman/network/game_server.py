"""
Game Server: WebSocket tabanlı multiplayer sunucu.
İki oyunculu Bomberman oyunu için merkezi sunucu.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import websockets
try:
    from websockets.legacy.server import WebSocketServerProtocol
except Exception:
    from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Server-Client mesaj tipleri."""
    # Client -> Server
    CREATE_ROOM = "create_room"
    JOIN_GAME = "join_game"
    PLAYER_MOVE = "player_move"
    PLACE_BOMB = "place_bomb"
    LEAVE_GAME = "leave_game"
    
    # Server -> Client
    ROOM_CREATED = "room_created"
    GAME_STATE = "game_state"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    GAME_STARTED = "game_started"
    GAME_OVER = "game_over"
    ERROR = "error"


@dataclass
class Player:
    """Oyuncu verisi."""
    player_id: str
    username: str
    websocket: WebSocketServerProtocol
    position: tuple[int, int] = (1, 1)
    health: int = 100
    ready: bool = False


@dataclass
class GameRoom:
    """Oyun odası - 2 oyuncu."""
    room_id: str
    room_code: str  # Paylaşılabilir 6 haneli kod
    players: list[Player] = field(default_factory=list)
    started: bool = False
    level_id: str = "level_1"
    
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


class GameServer:
    """
    Bomberman multiplayer sunucusu.
    WebSocket ile client'ları yönetir.
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        """
        Sunucu başlatır.
        
        Args:
            host: Sunucu host adresi
            port: Sunucu port numarası
        """
        self.host = host
        self.port = port
        self.rooms: dict[str, GameRoom] = {}  # room_id -> GameRoom
        self.room_codes: dict[str, str] = {}  # room_code -> room_id
        
    async def start(self) -> None:
        """Sunucuyu başlat."""
        logger.info(f"Game server starting on {self.host}:{self.port}")
        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Sonsuz döngü
    
    async def handle_client(self, websocket: WebSocketServerProtocol) -> None:
        """
        Client bağlantısını yönet.
        
        Args:
            websocket: Client websocket bağlantısı
        """
        player_id = str(uuid.uuid4())
        logger.info(f"Client connected: {player_id}")
        
        try:
            async for message in websocket:
                await self.handle_message(player_id, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {player_id}")
        finally:
            await self.handle_disconnect(player_id)
    
    async def handle_message(
        self, 
        player_id: str, 
        websocket: WebSocketServerProtocol, 
        message: str
    ) -> None:
        """
        Client mesajını işle.
        
        Args:
            player_id: Oyuncu ID'si
            websocket: Client websocket
            message: JSON mesaj
        """
        try:
            data = json.loads(message)
            msg_type = MessageType(data.get("type"))
            
            if msg_type == MessageType.CREATE_ROOM:
                await self.handle_create_room(player_id, websocket, data)
            
            elif msg_type == MessageType.JOIN_GAME:
                await self.handle_join_game(player_id, websocket, data)
            
            elif msg_type == MessageType.PLAYER_MOVE:
                await self.handle_player_move(player_id, data)
            
            elif msg_type == MessageType.PLACE_BOMB:
                await self.handle_place_bomb(player_id, data)
            
            elif msg_type == MessageType.LEAVE_GAME:
                await self.handle_leave_game(player_id)
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid message from {player_id}: {e}")
            await self.send_error(websocket, "Invalid message format")
    
    def _generate_room_code(self) -> str:
        """6 haneli benzersiz oda kodu oluştur."""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in self.room_codes:
                return code
    
    async def handle_create_room(
        self,
        player_id: str,
        websocket: WebSocketServerProtocol,
        data: dict[str, Any]
    ) -> None:
        """Yeni oda oluştur."""
        username = data.get("username", f"Player_{player_id[:8]}")
        
        # Yeni oda oluştur
        room_id = str(uuid.uuid4())
        room_code = self._generate_room_code()
        room = GameRoom(room_id=room_id, room_code=room_code)
        
        # Oluşturan oyuncuyu ekle
        player = Player(player_id=player_id, username=username, websocket=websocket)
        room.add_player(player)
        
        # Odayı kaydet
        self.rooms[room_id] = room
        self.room_codes[room_code] = room_id
        
        logger.info(f"Player {username} created room {room_code} ({room_id})")
        
        # Client'a oda kodu gönder
        await websocket.send(json.dumps({
            "type": MessageType.ROOM_CREATED.value,
            "room_code": room_code,
            "room_id": room_id,
            "player_count": 1
        }))
    
    async def handle_join_game(
        self, 
        player_id: str, 
        websocket: WebSocketServerProtocol, 
        data: dict[str, Any]
    ) -> None:
        """Oyuncu odaya katıl."""
        username = data.get("username", f"Player_{player_id[:8]}")
        room_code = data.get("room_code", "").strip().upper()
        
        # Oda kodunu kontrol et
        if not room_code or room_code not in self.room_codes:
            await self.send_error(websocket, "Geçersiz oda kodu")
            return
        
        room_id = self.room_codes[room_code]
        room = self.rooms.get(room_id)
        
        if not room:
            await self.send_error(websocket, "Oda bulunamadı")
            return
        
        if room.is_full():
            await self.send_error(websocket, "Oda dolu")
            return
        
        if room.started:
            await self.send_error(websocket, "Oyun zaten başlamış")
            return
        
        # Oyuncuyu odaya ekle
        player = Player(player_id=player_id, username=username, websocket=websocket)
        room.add_player(player)
        
        logger.info(f"Player {username} joined room {room_code}")
        
        # Odadaki tüm oyunculara bildir
        await self.broadcast_to_room(
            room_id,
            {
                "type": MessageType.PLAYER_JOINED.value,
                "player_id": player_id,
                "username": username,
                "player_count": len(room.players)
            }
        )
        
        # Oda doluysa oyunu başlat
        if room.is_full():
            await self.start_game(room_id)
    
    async def handle_player_move(self, player_id: str, data: dict[str, Any]) -> None:
        """Oyuncu hareket."""
        room = self.find_player_room(player_id)
        if not room:
            return
        
        player = room.get_player(player_id)
        if player:
            direction = data.get("direction")  # "up", "down", "left", "right"
            # Hareket işlemi (game logic'de yapılacak)
            
            # Tüm oyunculara state broadcast et
            await self.broadcast_game_state(room.room_id)
    
    async def handle_place_bomb(self, player_id: str, data: dict[str, Any]) -> None:
        """Oyuncu bomba koydu."""
        room = self.find_player_room(player_id)
        if not room:
            return
        
        # Bomba yerleştirme (game logic'de yapılacak)
        await self.broadcast_game_state(room.room_id)
    
    async def handle_leave_game(self, player_id: str) -> None:
        """Oyuncu oyundan çıktı."""
        room = self.find_player_room(player_id)
        if not room:
            return
        
        player = room.remove_player(player_id)
        if player:
            logger.info(f"Player {player.username} left room {room.room_id}")
            
            await self.broadcast_to_room(
                room.room_id,
                {
                    "type": MessageType.PLAYER_LEFT.value,
                    "player_id": player_id
                }
            )
    
    async def handle_disconnect(self, player_id: str) -> None:
        """Client bağlantısı koptu."""
        await self.handle_leave_game(player_id)
    
    async def start_game(self, room_id: str) -> None:
        """Oyunu başlat."""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        room.started = True
        logger.info(f"Game started in room {room_id}")
        
        await self.broadcast_to_room(
            room_id,
            {
                "type": MessageType.GAME_STARTED.value,
                "level_id": room.level_id,
                "players": [
                    {
                        "player_id": p.player_id,
                        "username": p.username,
                        "position": p.position
                    }
                    for p in room.players
                ]
            }
        )
    
    async def broadcast_game_state(self, room_id: str) -> None:
        """Oyun state'ini tüm oyunculara gönder."""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        state = {
            "type": MessageType.GAME_STATE.value,
            "players": [
                {
                    "player_id": p.player_id,
                    "position": p.position,
                    "health": p.health
                }
                for p in room.players
            ]
        }
        
        await self.broadcast_to_room(room_id, state)
    
    async def broadcast_to_room(self, room_id: str, message: dict[str, Any]) -> None:
        """Odadaki tüm oyunculara mesaj gönder."""
        room = self.rooms.get(room_id)
        if not room:
            return
        
        message_json = json.dumps(message)
        
        for player in room.players:
            try:
                await player.websocket.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"Could not send to {player.player_id}, connection closed")
    
    async def send_error(self, websocket: WebSocketServerProtocol, error_msg: str) -> None:
        """Client'a hata mesajı gönder."""
        message = {
            "type": MessageType.ERROR.value,
            "message": error_msg
        }
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            pass
    
    def find_player_room(self, player_id: str) -> Optional[GameRoom]:
        """Oyuncunun bulunduğu odayı bul."""
        for room in self.rooms.values():
            if room.get_player(player_id):
                return room
        return None


async def main():
    """Sunucuyu başlat."""
    server = GameServer(host="0.0.0.0", port=8765)
    await server.start()


if __name__ == "__main__":
    asyncio.run(main())
