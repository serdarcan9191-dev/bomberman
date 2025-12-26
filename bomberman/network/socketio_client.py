"""
Socket.io Client: Bomberman multiplayer için socket.io client
Local server'a bağlanır (http://localhost:7777)
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Optional

import socketio

logger = logging.getLogger(__name__)


class SocketIOClient:
    """
    Bomberman multiplayer socket.io client.
    Backend server'a bağlanır ve oyun eventlerini yönetir.
    """
    
    def __init__(self, server_url: str = "http://localhost:7777") -> None:
        """
        Client başlatır.
        
        Args:
            server_url: Socket.io server URL'i
        """
        self.server_url = server_url
        self.sio: Optional[socketio.Client] = None
        self.connected: bool = False
        self.player_id: Optional[str] = None
        self.room_code: Optional[str] = None
        self.username: Optional[str] = None  # Kullanıcı adı
        
        # Event callbacks
        self._on_room_created: Optional[Callable[[dict], None]] = None
        self._on_game_state: Optional[Callable[[dict], None]] = None
        self._on_player_joined: Optional[Callable[[dict], None]] = None
        self._on_player_left: Optional[Callable[[dict], None]] = None
        self._on_game_started: Optional[Callable[[dict], None]] = None
        self._on_game_over: Optional[Callable[[dict], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_rooms_list: Optional[Callable[[dict], None]] = None
        self._on_room_deleted: Optional[Callable[[dict], None]] = None
    
    def connect(self) -> bool:
        """
        Sunucuya bağlan (synchronous).
        
        Returns:
            bool: Başarılı mı?
        """
        try:
            self.sio = socketio.Client()
            
            # Bağlantı event'i için flag
            connection_event = threading.Event()
            connection_error = [None]
            
            # Event handler'ları ayarla (connect event'inden önce)
            @self.sio.event
            def connect():
                """Bağlantı kuruldu."""
                logger.info("Socket.io connected")
                self.connected = True
                print(f"✅ Socket.io bağlantısı kuruldu: {self.server_url}")
                connection_event.set()
            
            @self.sio.event
            def disconnect():
                """Bağlantı koptu."""
                logger.info("Socket.io disconnected")
                self.connected = False
            
            # Diğer event handler'ları ayarla
            self._setup_event_handlers()
            
            # Bağlantıyı thread'de yap (blocking olmaması için)
            def connect_thread():
                try:
                    self.sio.connect(self.server_url, wait_timeout=5)
                    logger.info(f"Connection attempt to server: {self.server_url}")
                    # Event loop'u çalıştır (connect event'i tetiklenecek)
                    self.sio.wait()
                except Exception as e:
                    logger.error(f"Connection failed: {e}")
                    connection_error[0] = e
                    self.connected = False
                    connection_event.set()
            
            thread = threading.Thread(target=connect_thread, daemon=True)
            thread.start()
            
            # Bağlantının kurulmasını bekle (max 3 saniye)
            if connection_event.wait(timeout=3):
                if connection_error[0] is None and self.connected:
                    return True
                else:
                    logger.error(f"Connection error: {connection_error[0]}")
                    return False
            else:
                logger.warning("Connection timeout - server may not be running")
                return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return False
    
    def _setup_event_handlers(self) -> None:
        """Socket.io event handler'larını ayarla (connect/disconnect hariç - onlar connect() içinde)."""
        if not self.sio:
            return
        
        @self.sio.on("room_created")
        def on_room_created(data: dict):
            """Oda oluşturuldu."""
            logger.info(f"Room created: {data}")
            self.room_code = data.get("room_code")
            self.player_id = data.get("player_id")
            if self._on_room_created:
                self._on_room_created(data)
        
        @self.sio.on("player_joined")
        def on_player_joined(data: dict):
            """Oyuncu katıldı."""
            logger.info(f"Player joined: {data}")
            self.room_code = data.get("room_code")
            self.player_id = data.get("player_id")
            if self._on_player_joined:
                self._on_player_joined(data)
        
        @self.sio.on("game_started")
        def on_game_started(data: dict):
            """Oyun başladı."""
            logger.info(f"Game started: {data}")
            if self._on_game_started:
                self._on_game_started(data)
        
        @self.sio.on("game_state")
        def on_game_state(data: dict):
            """Oyun state güncellemesi."""
            # Debug: destroyed_walls varsa logla
            destroyed_walls = data.get("destroyed_walls", [])
            if destroyed_walls:
                logger.info(f"📦 Received game_state with {len(destroyed_walls)} destroyed walls: {destroyed_walls}")
            if self._on_game_state:
                self._on_game_state(data)
        
        @self.sio.on("player_left")
        def on_player_left(data: dict):
            """Oyuncu çıktı."""
            logger.info(f"Player left: {data}")
            if self._on_player_left:
                self._on_player_left(data)
        
        @self.sio.on("room_deleted")
        def on_room_deleted(data: dict):
            """Oda silindi."""
            logger.info(f"Room deleted: {data}")
            if self._on_room_deleted:
                self._on_room_deleted(data)
        
        @self.sio.on("error")
        def on_error(data: dict):
            """Hata mesajı."""
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Server error: {error_msg}")
            if self._on_error:
                self._on_error(error_msg)
        
        @self.sio.on("rooms_list")
        def on_rooms_list(data: dict):
            """Oda listesi geldi."""
            logger.info(f"📋 Rooms list event received!")
            logger.info(f"📋 Data type: {type(data)}, Data: {data}")
            
            # Data formatını kontrol et
            if isinstance(data, dict):
                rooms_count = len(data.get("rooms", []))
                logger.info(f"📋 Found {rooms_count} rooms in data")
            else:
                logger.warning(f"⚠️ Unexpected data type: {type(data)}")
            
            if self._on_rooms_list:
                logger.info("✅ Calling _on_rooms_list callback")
                self._on_rooms_list(data)
            else:
                logger.warning("⚠️ _on_rooms_list callback not set!")
    
    def disconnect(self) -> None:
        """Sunucu bağlantısını kes."""
        if self.sio and self.connected:
            try:
                self.sio.disconnect()
            except:
                pass
            self.connected = False
            logger.info("Disconnected from server")
    
    def create_room(self, username: str) -> None:
        """
        Yeni oda oluştur.
        
        Args:
            username: Oyuncu adı
        """
        if not self.sio or not self.connected:
            logger.warning("Not connected to server")
            return
        
        self.username = username  # Username'i kaydet
        try:
            # Oda oluştur (emit ile gönder, response event listener ile alınacak)
            self.sio.emit("create_room", {"username": username})
            logger.info(f"Create room request sent for {username}")
        except Exception as e:
            logger.error(f"Failed to create room: {e}")
            if self._on_error:
                self._on_error(f"Oda oluşturulamadı: {str(e)}")
    
    def join_room(self, username: str, room_code: str) -> None:
        """
        Odaya katıl.
        
        Args:
            username: Oyuncu adı
            room_code: Oda kodu
        """
        if not self.sio or not self.connected:
            logger.warning("Not connected to server")
            return
        
        self.username = username  # Username'i kaydet
        try:
            # Odaya katıl (emit ile gönder, response event listener ile alınacak)
            self.sio.emit("join_room", {
                "username": username,
                "room_code": room_code
            })
            logger.info(f"Join room request sent for {username} to room {room_code}")
        except Exception as e:
            logger.error(f"Failed to join room: {e}")
            if self._on_error:
                self._on_error(f"Odaya katılamadı: {str(e)}")
    
    def send_move(self, direction: str) -> None:
        """
        Hareket komutu gönder.
        
        Args:
            direction: "up", "down", "left", "right"
        """
        if not self.sio or not self.connected:
            logger.warning("Not connected to server")
            return
        
        try:
            self.sio.emit("player_move", {"direction": direction})
        except Exception as e:
            logger.error(f"Failed to send move: {e}")
    
    def send_place_bomb(self) -> None:
        """Bomba koyma komutu gönder."""
        if not self.sio or not self.connected:
            logger.warning("Not connected to server")
            return
        
        try:
            self.sio.emit("place_bomb", {})
        except Exception as e:
            logger.error(f"Failed to send place bomb: {e}")
    
    def send_player_damage(self, damage: int) -> None:
        """
        Oyuncu hasar bildir (düşman hasarı için).
        
        Args:
            damage: Hasar miktarı
        """
        if not self.sio or not self.connected:
            logger.warning("Not connected to server")
            return
        
        try:
            self.sio.emit("player_damage", {"damage": damage})
        except Exception as e:
            logger.error(f"Failed to send player damage: {e}")
    
    def leave_room(self) -> None:
        """Odadan çık."""
        if not self.sio or not self.connected:
            return
        
        try:
            self.sio.emit("leave_room", {})
        except Exception as e:
            logger.error(f"Failed to leave room: {e}")
        finally:
            self.room_code = None
            self.player_id = None
    
    def list_rooms(self) -> None:
        """Aktif odaları listele."""
        print(f"🔍 list_rooms() çağrıldı")
        print(f"   sio: {self.sio is not None}, connected: {self.connected}")
        
        if not self.sio or not self.connected:
            logger.warning("❌ Not connected to server - sio or connected is False")
            print(f"❌ list_rooms başarısız: sio={self.sio is not None}, connected={self.connected}")
            return
        
        try:
            print(f"📤 Emitting 'list_rooms' event...")
            self.sio.emit("list_rooms", {})
            logger.info("✅ List rooms request sent")
            print(f"✅ 'list_rooms' event gönderildi")
        except Exception as e:
            logger.error(f"❌ Failed to list rooms: {e}")
            print(f"❌ list_rooms hatası: {e}")
    
    def on_rooms_list(self, callback: Callable[[dict], None]) -> None:
        """Oda listesi callback'ini ayarla."""
        self._on_rooms_list = callback
    
    # Event callback setters
    def on_room_created(self, callback: Callable[[dict], None]) -> None:
        """Oda oluşturuldu callback'i."""
        self._on_room_created = callback
    
    def on_game_state(self, callback: Callable[[dict], None]) -> None:
        """Oyun state güncellemesi callback'i."""
        self._on_game_state = callback
    
    def on_player_joined(self, callback: Callable[[dict], None]) -> None:
        """Oyuncu katıldı callback'i."""
        self._on_player_joined = callback
    
    def on_player_left(self, callback: Callable[[dict], None]) -> None:
        """Oyuncu çıktı callback'i."""
        self._on_player_left = callback
    
    def on_room_deleted(self, callback: Callable[[dict], None]) -> None:
        """Oda silindi callback'i."""
        self._on_room_deleted = callback
    
    def on_game_started(self, callback: Callable[[dict], None]) -> None:
        """Oyun başladı callback'i."""
        self._on_game_started = callback
    
    def on_game_over(self, callback: Callable[[dict], None]) -> None:
        """Oyun bitti callback'i."""
        self._on_game_over = callback
    
    def on_error(self, callback: Callable[[str], None]) -> None:
        """Hata callback'i."""
        self._on_error = callback

