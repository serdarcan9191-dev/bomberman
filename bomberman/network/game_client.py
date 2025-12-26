"""
Game Client: WebSocket tabanlı multiplayer client.
Sunucuya bağlanır ve oyun eventlerini yönetir.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Optional

import websockets
from websockets.client import WebSocketClientProtocol

from network.game_server import MessageType

logger = logging.getLogger(__name__)


class GameClient:
    """
    Bomberman multiplayer client.
    Sunucuya bağlanır ve mesaj alışverişi yapar.
    """
    
    def __init__(self, server_url: str = "ws://localhost:8765") -> None:
        """
        Client başlatır.
        
        Args:
            server_url: Sunucu WebSocket URL'i
        """
        self.server_url = server_url
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.connected: bool = False
        self.player_id: Optional[str] = None
        
        # Event callbacks
        self._on_room_created: Optional[Callable[[dict], None]] = None
        self._on_game_state: Optional[Callable[[dict], None]] = None
        self._on_player_joined: Optional[Callable[[dict], None]] = None
        self._on_player_left: Optional[Callable[[dict], None]] = None
        self._on_game_started: Optional[Callable[[dict], None]] = None
        self._on_game_over: Optional[Callable[[dict], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
    
    async def connect(self) -> bool:
        """
        Sunucuya bağlan.
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info(f"Connected to server: {self.server_url}")
            
            # Mesaj dinlemeyi başlat
            asyncio.create_task(self._listen_messages())
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Sunucu bağlantısını kes."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from server")
    
    async def create_room(self, username: str) -> None:
        """
        Yeni oda oluştur.
        
        Args:
            username: Oyuncu adı
        """
        message = {
            "type": "create_room",
            "username": username
        }
        await self._send_message(message)
    
    async def join_game(self, username: str, room_code: str) -> None:
        """
        Odaya katıl.
        
        Args:
            username: Oyuncu adı
            room_code: Oda kodu
        """
        message = {
            "type": "join_game",
            "username": username,
            "room_code": room_code
        }
        await self._send_message(message)
    
    async def send_move(self, direction: str) -> None:
        """
        Hareket komutu gönder.
        
        Args:
            direction: "up", "down", "left", "right"
        """
        message = {
            "type": MessageType.PLAYER_MOVE.value,
            "direction": direction
        }
        await self._send_message(message)
    
    async def send_place_bomb(self) -> None:
        """Bomba koyma komutu gönder."""
        message = {
            "type": MessageType.PLACE_BOMB.value
        }
        await self._send_message(message)
    
    async def leave_game(self) -> None:
        """Oyundan çık."""
        message = {
            "type": MessageType.LEAVE_GAME.value
        }
        await self._send_message(message)
    
    async def _send_message(self, message: dict[str, Any]) -> None:
        """
        Sunucuya mesaj gönder.
        
        Args:
            message: JSON mesaj
        """
        if not self.websocket or not self.connected:
            logger.warning("Not connected to server")
            return
        
        try:
            msg_json = json.dumps(message)
            logger.info(f"Sending message: {msg_json}")
            await self.websocket.send(msg_json)
            logger.info("Message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    async def _listen_messages(self) -> None:
        """Sunucudan gelen mesajları dinle."""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed by server")
            self.connected = False
    
    async def _handle_message(self, message: str) -> None:
        """
        Sunucudan gelen mesajı işle.
        
        Args:
            message: JSON mesaj
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            logger.info(f"Received message type: {msg_type}, data: {data}")
            
            if msg_type == "room_created":
                logger.info(f"Room created callback called with data: {data}")
                if self._on_room_created:
                    self._on_room_created(data)
                else:
                    logger.warning("_on_room_created callback not set!")
            
            elif msg_type == MessageType.GAME_STATE.value:
                if self._on_game_state:
                    self._on_game_state(data)
            
            elif msg_type == MessageType.PLAYER_JOINED.value:
                if self._on_player_joined:
                    self._on_player_joined(data)
            
            elif msg_type == MessageType.PLAYER_LEFT.value:
                if self._on_player_left:
                    self._on_player_left(data)
            
            elif msg_type == MessageType.GAME_STARTED.value:
                if self._on_game_started:
                    self._on_game_started(data)
            
            elif msg_type == MessageType.GAME_OVER.value:
                if self._on_game_over:
                    self._on_game_over(data)
            
            elif msg_type == MessageType.ERROR.value:
                error_msg = data.get("message", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                if self._on_error:
                    self._on_error(error_msg)
                    
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid message from server: {e}")
    
    # Event callback setters
    def on_game_state(self, callback: Callable[[dict], None]) -> None:
        """Oyun state güncellemesi callback'i."""
        self._on_game_state = callback
    
    def on_player_joined(self, callback: Callable[[dict], None]) -> None:
        """Oyuncu katıldı callback'i."""
        self._on_player_joined = callback
    
    def on_player_left(self, callback: Callable[[dict], None]) -> None:
        """Oyuncu çıktı callback'i."""
        self._on_player_left = callback
    
    def on_game_started(self, callback: Callable[[dict], None]) -> None:
        """Oyun başladı callback'i."""
        self._on_game_started = callback
    
    def on_game_over(self, callback: Callable[[dict], None]) -> None:
        """Oyun bitti callback'i."""
        self._on_game_over = callback
    
    def on_error(self, callback: Callable[[str], None]) -> None:
        """Hata callback'i."""
        self._on_error = callback
