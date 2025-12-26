"""
Multiplayer Lobby Screen: Oda oluştur veya katıl seçimi
Socket.io ile backend server'a bağlanır
"""
from __future__ import annotations

import logging
import pygame
import pyperclip
from typing import Callable, Optional

logger = logging.getLogger(__name__)

from network.socketio_client import SocketIOClient
from service.auth_service import AuthService
from view.main_menu import MenuTheme
from view.scene import Scene
from view.scene_manager import SceneManager
from view.terminal_theme import get_terminal_font, draw_terminal_text, draw_terminal_box


class MultiplayerLobbyScreen(Scene):
    """Multiplayer lobi - Oda oluştur veya katıl seçimi."""
    
    def __init__(
        self,
        manager: SceneManager,
        theme: MenuTheme,
        auth_service: AuthService,
        server_url: str = "http://localhost:7777",
        game_controller=None,
        game_scene=None,
        loading_scene=None,
    ) -> None:
        self._manager = manager
        self._theme = theme
        self._auth_service = auth_service
        self._server_url = server_url
        self._game_controller = game_controller
        self._game_scene = game_scene
        self._loading_scene = loading_scene
        
        # Socket.io client
        self._client: Optional[SocketIOClient] = None
        self._connected = False
        
        # Input state
        self._room_code_input: str = ""
        self._error_message: str = ""
        self._mode: str = "select"  # "select", "create", "join", "waiting"
        
        # Oda listesi özelliği kaldırıldı - sadece oda kodu ile bağlanma
        
        # Room state
        self._room_code: Optional[str] = None
        self._player_count: int = 0
        self._waiting_for_players: bool = False
        self._copy_message: str = ""  # Kopyalama mesajı
        self._copy_message_timer: float = 0.0  # Mesaj gösterim süresi
        
        # Loading states
        self._creating_room: bool = False  # Oda oluşturuluyor
        self._joining_room: bool = False  # Odaya katılıyor
        self._loading_timer: float = 0.0  # Loading animasyonu için
        self._cursor_timer: float = 0.0  # Cursor animasyonu için
        
        # UI - Terminal fontlar
        self._title_font = get_terminal_font(40)
        self._button_font = get_terminal_font(20)
        self._label_font = get_terminal_font(18)
        self._input_font = get_terminal_font(18)
        self._hint_font = get_terminal_font(14)
        self._selected_button = 0  # 0: Create, 1: Join
        self._join_button_rect: Optional[pygame.Rect] = None  # Odaya katıl butonu pozisyonu
        self._back_button_rect: Optional[pygame.Rect] = None  # Geri butonu pozisyonu
    
    def handle_events(self, events) -> None:
        for event in events:
            # Mouse click - Buton kontrolü
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._back_button_rect and self._back_button_rect.collidepoint(event.pos):
                    self._handle_back()
                    continue
                # Odaya katıl butonu
                if self._mode == "join" and self._join_button_rect and self._join_button_rect.collidepoint(event.pos):
                    if self._room_code_input and self._room_code_input.strip() and not self._joining_room:
                        self._joining_room = True
                        self._join_room()
                        print(f"✅ Odaya katıl butonu tıklandı: {self._room_code_input}")
                    continue
            
            # Mouse hover ve click için select mode
            elif event.type == pygame.MOUSEMOTION and self._mode == "select":
                width, height = pygame.display.get_surface().get_size()
                create_rect = pygame.Rect(width // 2 - 200, 230, 400, 80)
                join_rect = pygame.Rect(width // 2 - 200, 310, 400, 80)
                if create_rect.collidepoint(event.pos):
                    self._selected_button = 0
                elif join_rect.collidepoint(event.pos):
                    self._selected_button = 1
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._mode == "select":
                width, height = pygame.display.get_surface().get_size()
                create_rect = pygame.Rect(width // 2 - 200, 230, 400, 80)
                join_rect = pygame.Rect(width // 2 - 200, 310, 400, 80)
                if create_rect.collidepoint(event.pos):
                    self._mode = "create"
                    self._create_room()
                elif join_rect.collidepoint(event.pos):
                    self._mode = "join"
                    self._room_code_input = ""
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._handle_back()
                    continue
                
                elif self._mode == "select":
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        self._selected_button = (self._selected_button + 1) % 2
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self._selected_button = (self._selected_button - 1) % 2
                    elif event.key == pygame.K_RETURN:
                        if self._selected_button == 0:
                            self._mode = "create"
                            self._create_room()
                        elif self._selected_button == 1:
                            self._mode = "join"
                            self._room_code_input = ""
                
                elif self._mode == "create":
                    if self._waiting_for_players:
                        # Bekleme ekranında
                        if event.key == pygame.K_c:
                            # Oda kodunu kopyala
                            self._copy_room_code()
                    else:
                        if event.key == pygame.K_RETURN:
                            if not self._creating_room:
                                self._creating_room = True
                                self._create_room()
                
                elif self._mode == "join":
                    if not self._joining_room:  # Sadece loading durumunda değilken input al
                        # ENTER - Odaya katıl
                        if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                            if self._room_code_input and self._room_code_input.strip():
                                self._joining_room = True
                                self._join_room()
                        
                        # BACKSPACE - Sil
                        elif event.key == pygame.K_BACKSPACE:
                            if self._room_code_input:
                                self._room_code_input = self._room_code_input[:-1]
                        
                        # CTRL+V - Yapıştır
                        elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                            try:
                                clipboard_text = pyperclip.paste()
                                if clipboard_text:
                                    cleaned = ''.join(c.upper() for c in clipboard_text if c.isalnum())[:6]
                                    if cleaned:
                                        self._room_code_input = cleaned
                            except Exception:
                                pass
                        
                        # Normal karakter girişi - BASIT
                        elif event.unicode:
                            char = event.unicode.upper()
                            # Sadece harf ve rakam kabul et
                            if char.isalnum() and len(self._room_code_input) < 6:
                                self._room_code_input += char
                
    
    def update(self, delta: float) -> None:
        # Bağlantı kontrolü
        if not self._client:
            self._connect()
        elif self._client:
            # Bağlantı durumunu güncelle (connected property'yi kontrol et)
            was_connected = self._connected
            if self._client.connected:
                if not self._connected:
                    self._connected = True
                    self._error_message = ""
                    print(f"✅ Bağlantı durumu güncellendi: connected=True")
                    # Eğer oda listesi modundaysak ve bağlantı yeni kurulduysa, list_rooms çağır
                    if self._mode == "room_list" and not was_connected:
                        print(f"🔄 Bağlantı kuruldu, oda listesi otomatik yenileniyor...")
                        self._loading_rooms = True
                        self._client.list_rooms()
            else:
                if self._connected:
                    self._connected = False
                    print(f"⚠️ Bağlantı durumu güncellendi: connected=False")
        
        # Kopyalama mesajı timer'ı
        if self._copy_message_timer > 0:
            self._copy_message_timer -= delta
            if self._copy_message_timer <= 0:
                self._copy_message = ""
        
        # Loading animasyonu için timer
        self._loading_timer += delta
        
        # Cursor animasyonu için timer
        if self._mode == "join" and not self._joining_room:
            self._cursor_timer += delta * 2.0  # Cursor yanıp sönsün
    
    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(self._theme.background)
        width, height = screen.get_size()
        
        if self._mode == "select":
            self._draw_selection_screen(screen, width, height)
        elif self._mode == "create":
            if self._waiting_for_players:
                self._draw_waiting_screen(screen, width, height)
            else:
                self._draw_create_screen(screen, width, height)
        elif self._mode == "join":
            self._draw_join_screen(screen, width, height)
        
        # Geri butonu her modda gösterilir (select modunda değil)
        if self._mode != "select":
            self._draw_back_button(screen, width, height)
    
    def _draw_selection_screen(self, screen, width, height):
        """Terminal stili seçim ekranı"""
        # Terminal başlık
        draw_terminal_text(screen, "COK OYUNCULU", self._title_font, self._theme.title, (width // 2, 60), "center")
        
        # Connection status - terminal stili
        status_rect = pygame.Rect(width // 2 - 150, 120, 300, 40)
        if self._connected:
            status_text = "BAGLANDI"
            status_color = (255, 255, 255)
        else:
            dots = "." * (int(self._loading_timer * 2) % 4)
            status_text = f"BAGLANIYOR{dots}"
            status_color = (200, 200, 200)
        
        draw_terminal_box(screen, status_rect, status_color, self._theme.panel, 2)
        draw_terminal_text(screen, status_text, self._hint_font, status_color, status_rect.center, "center")
        
        # Create Room Button - terminal stili
        create_rect = pygame.Rect(width // 2 - 200, 200, 400, 50)
        is_selected = self._selected_button == 0
        border_color = self._theme.accent if is_selected else self._theme.panel_accent
        fill_color = self._theme.panel if is_selected else self._theme.background
        draw_terminal_box(screen, create_rect, border_color, fill_color, 2)
        text_color = self._theme.title if is_selected else self._theme.text
        draw_terminal_text(screen, "ODA OLUSTUR", self._button_font, text_color, create_rect.center, "center")
        
        # Join Room Button - terminal stili
        join_rect = pygame.Rect(width // 2 - 200, 270, 400, 50)
        is_selected = self._selected_button == 1
        border_color = self._theme.accent if is_selected else self._theme.panel_accent
        fill_color = self._theme.panel if is_selected else self._theme.background
        draw_terminal_box(screen, join_rect, border_color, fill_color, 2)
        text_color = self._theme.title if is_selected else self._theme.text
        draw_terminal_text(screen, "ODA KODU ILE KATIL", self._button_font, text_color, join_rect.center, "center")
        
        # Hints
        draw_terminal_text(screen, "YUKARI/ASAGI: Secim  |  ENTER: Onayla", self._hint_font, self._theme.text, (width // 2, 350), "center")
    
    def _draw_create_screen(self, screen, width, height):
        """Terminal stili oda oluşturma ekranı"""
        if self._creating_room:
            dots = "." * (int(self._loading_timer * 3) % 4)
            draw_terminal_text(screen, f"ODA OLUSTURULUYOR{dots}", self._title_font, self._theme.title, (width // 2, 80), "center")
            draw_terminal_text(screen, "Lutfen bekleyin...", self._label_font, self._theme.text, (width // 2, 200), "center")
            return
        
        draw_terminal_text(screen, "ODA OLUSTUR", self._title_font, self._theme.title, (width // 2, 80), "center")
        
        username = self._auth_service.get_current_username() or "Bilinmeyen"
        draw_terminal_text(screen, f"Kullanici: {username}", self._label_font, self._theme.text, (width // 2, 180), "center")
        
        draw_terminal_text(screen, "Oda olusturulduktan sonra oda kodunu arkadasina gonder", self._hint_font, self._theme.text, (width // 2, 240), "center")
        draw_terminal_text(screen, "ENTER: Oda Olustur", self._hint_font, self._theme.panel_accent, (width // 2, 300), "center")
        
        if self._error_message:
            draw_terminal_text(screen, self._error_message, self._label_font, (255, 100, 100), (width // 2, 360), "center")
    
    def _draw_waiting_screen(self, screen, width, height):
        """Terminal stili bekleme ekranı"""
        draw_terminal_text(screen, "ODA HAZIR", self._title_font, (255, 255, 255), (width // 2, 60), "center")
        
        if self._room_code:
            draw_terminal_text(screen, "Oda Kodu:", self._label_font, (255, 255, 255), (width // 2, 150), "center")
            
            # Büyük oda kodu - terminal font
            code_font = get_terminal_font(48)
            draw_terminal_text(screen, self._room_code, code_font, (255, 255, 255), (width // 2, 220), "center")
            
            draw_terminal_text(screen, "C: Oda Kodunu Kopyala", self._hint_font, (200, 200, 200), (width // 2, 280), "center")
            
            if self._copy_message:
                draw_terminal_text(screen, self._copy_message, self._label_font, (255, 255, 255), (width // 2, 320), "center")
        
        player_color = (255, 255, 255) if self._player_count >= 2 else (200, 200, 200)
        draw_terminal_text(screen, f"Oyuncular: {self._player_count}/2", self._label_font, player_color, (width // 2, 360), "center")
        
        if self._player_count < 2:
            draw_terminal_text(screen, "Ikinci oyuncu bekleniyor...", self._hint_font, (200, 200, 200), (width // 2, 400), "center")
        else:
            draw_terminal_text(screen, "Oyun baslamak uzere...", self._label_font, (255, 255, 255), (width // 2, 400), "center")
        
        if self._error_message:
            draw_terminal_text(screen, self._error_message, self._label_font, (255, 100, 100), (width // 2, 450), "center")
    
    def _draw_join_screen(self, screen, width, height):
        """Terminal stili odaya katılma ekranı"""
        if self._joining_room:
            dots = "." * (int(self._loading_timer * 3) % 4)
            draw_terminal_text(screen, f"ODAYA KATILINIYOR{dots}", self._title_font, self._theme.title, (width // 2, 80), "center")
            draw_terminal_text(screen, "Lutfen bekleyin...", self._label_font, self._theme.text, (width // 2, 180), "center")
            draw_terminal_text(screen, f"Oda: {self._room_code_input}", self._label_font, self._theme.text, (width // 2, 240), "center")
            return
        
        draw_terminal_text(screen, "ODAYA KATIL", self._title_font, self._theme.title, (width // 2, 60), "center")
        
        username = self._auth_service.get_current_username() or "Bilinmeyen"
        draw_terminal_text(screen, f"Kullanici: {username}", self._label_font, self._theme.text, (width // 2, 140), "center")
        
        # Room code input - terminal stili
        self._render_input_box_terminal(screen, "Oda Kodu:", self._room_code_input, 220, True, width)
        
        # Odaya Katıl butonu - terminal stili
        button_width = 300
        button_height = 45
        button_x = width // 2 - button_width // 2
        button_y = 300
        
        self._join_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        is_button_enabled = bool(self._room_code_input.strip()) and not self._joining_room
        border_color = self._theme.accent if is_button_enabled else self._theme.panel_accent
        fill_color = self._theme.panel if is_button_enabled else self._theme.background
        draw_terminal_box(screen, self._join_button_rect, border_color, fill_color, 2)
        
        text_color = self._theme.title if is_button_enabled else (50, 50, 50)
        draw_terminal_text(screen, "ODAYA KATIL", self._button_font, text_color, self._join_button_rect.center, "center")
        
        draw_terminal_text(screen, "CTRL+V: Yapistir", self._hint_font, self._theme.panel_accent, (width // 2, 370), "center")
        
        if self._error_message:
            draw_terminal_text(screen, self._error_message, self._label_font, (255, 100, 100), (width // 2, 400), "center")
    
    
    def _render_input_box(self, screen, label, value, y_pos, is_active, width):
        """Input box çiz (eski metod - terminal stili için _render_input_box_terminal kullan)"""
        self._render_input_box_terminal(screen, label, value, y_pos, is_active, width)
    
    def _render_input_box_terminal(self, screen, label, value, y_pos, is_active, width):
        """Terminal stili input box"""
        draw_terminal_text(screen, label, self._label_font, self._theme.text, (width // 2, y_pos - 30), "center")
        
        box_width = 400
        box_height = 40
        box_rect = pygame.Rect((width - box_width) // 2, y_pos, box_width, box_height)
        
        border_color = self._theme.accent if is_active else self._theme.panel_accent
        fill_color = self._theme.panel
        draw_terminal_box(screen, box_rect, border_color, fill_color, 2)
        
        draw_terminal_text(screen, value, self._input_font, self._theme.text, (box_rect.left + 10, box_rect.centery), "left")
        
        # Cursor - aktif durumda
        if is_active:
            cursor_visible = int(self._cursor_timer) % 2 == 0
            if cursor_visible:
                if value:
                    text_width = self._input_font.size(value)[0]
                    cursor_x = box_rect.left + 10 + text_width
                else:
                    cursor_x = box_rect.left + 10
                pygame.draw.line(screen, self._theme.accent, (cursor_x, box_rect.top + 8), (cursor_x, box_rect.bottom - 8), 2)
    
    def _connect(self) -> None:
        """Server'a bağlan"""
        if self._client:
            # Eğer client varsa bağlantı durumunu kontrol et
            if self._client.connected:
                self._connected = True
            return
        
        try:
            self._client = SocketIOClient(self._server_url)
            
            # Event callbacks
            self._client.on_room_created(self._on_room_created)
            self._client.on_player_joined(self._on_player_joined)
            self._client.on_game_started(self._on_game_started)
            self._client.on_room_deleted(self._on_room_deleted)
            self._client.on_error(self._on_error)
            # Oda listesi özelliği kaldırıldı - sadece oda kodu ile bağlanma
            
            # Bağlan (non-blocking)
            print(f"🔌 Server'a bağlanılıyor: {self._server_url}")
            self._connected = self._client.connect()
            
            if self._connected:
                print("✅ Bağlantı başarılı!")
                self._error_message = ""
            else:
                print("❌ Bağlantı başarısız!")
                self._error_message = "Sunucuya bağlanılamadı!"
        except Exception as e:
            print(f"Connection error: {e}")
            self._error_message = f"Bağlantı hatası: {str(e)}"
            self._connected = False
    
    def _handle_back(self) -> None:
        """Geri butonu işleyicisi - loading screen ile"""
        if self._mode == "select":
            self._disconnect()
            self._manager.return_to_menu(show_loading=True)
        else:
            self._mode = "select"
            self._error_message = ""
    
    def _draw_back_button(self, screen: pygame.Surface, width: int, height: int) -> None:
        """Terminal stili geri butonu"""
        button_width = 200
        button_height = 40
        button_x = width // 2 - button_width // 2
        button_y = height - 60
        
        self._back_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        draw_terminal_box(screen, self._back_button_rect, self._theme.accent, self._theme.panel, 2)
        draw_terminal_text(screen, "GERI", self._button_font, self._theme.text, self._back_button_rect.center, "center")
    
    def _disconnect(self) -> None:
        """Server bağlantısını kes"""
        if self._client:
            self._client.disconnect()
            self._client = None
        self._connected = False
    
    def _create_room(self):
        """Oda oluştur"""
        if not self._client or not self._connected:
            self._error_message = "Sunucuya bağlanılamadı!"
            self._creating_room = False
            return
        
        username = self._auth_service.get_current_username()
        if not username:
            self._error_message = "Lütfen önce giriş yapın!"
            self._creating_room = False
            return
        
        self._error_message = ""
        self._creating_room = True
        self._client.create_room(username)
    
    def _join_room(self):
        """Odaya katıl"""
        if not self._client or not self._connected:
            self._error_message = "Sunucuya bağlanılamadı!"
            self._joining_room = False
            return
        
        username = self._auth_service.get_current_username()
        if not username:
            self._error_message = "Lütfen önce giriş yapın!"
            self._joining_room = False
            return
        
        if not self._room_code_input.strip():
            self._error_message = "Oda kodu gerekli!"
            self._joining_room = False
            return
        
        self._error_message = ""
        self._joining_room = True
        self._client.join_room(username, self._room_code_input)
    
    def _on_room_created(self, data: dict):
        """Oda oluşturuldu callback"""
        room_code = data.get("room_code", "")
        player_count = data.get("player_count", 1)
        
        self._room_code = room_code
        self._player_count = player_count
        self._waiting_for_players = True
        self._error_message = ""
        self._creating_room = False  # Loading state'i kapat
        
        print(f"✅ Oda oluşturuldu! Kod: {room_code}")
        
        # Oda oluşturulduğunda otomatik olarak kopyala
        if room_code:
            self._copy_room_code()
        
    
    def _on_player_joined(self, data: dict):
        """Oyuncu katıldı callback"""
        player_count = data.get("player_count", 0)
        self._player_count = player_count
        self._joining_room = False  # Loading state'i kapat
        
        print(f"👥 Oyuncu katıldı! Toplam: {player_count}/2")
        
        if player_count >= 2:
            print("🎮 Oyun başlamak üzere...")
    
    def _on_game_started(self, data: dict):
        """Oyun başladı callback"""
        print(f"🎮 Oyun başladı! {data}")
        self._error_message = ""  # Hata mesajını temizle
        
        # Oyunu başlat
        if self._game_controller and self._game_scene:
            level_id = data.get("level_id", "level_1")
            players = data.get("players", [])
            
            # Önce kendi player pozisyonumuzu server'dan al
            my_player_id = self._client.player_id if self._client else None
            my_start_position = None
            for player in players:
                player_id = player.get("player_id")
                position = player.get("position", [1, 1])
                
                # Pozisyon formatını normalize et
                if isinstance(position, list) and len(position) >= 2:
                    position_tuple = (position[0], position[1])
                elif isinstance(position, tuple):
                    position_tuple = position
                else:
                    position_tuple = (1, 1)
                
                # Player dict'ini güncelle
                player["position"] = position_tuple
                
                # Kendi pozisyonumuzu bul
                if player_id == my_player_id:
                    my_start_position = position_tuple
                    print(f"📍 Kendi başlangıç pozisyonum: {my_start_position}")
            
            # Level yükleme artık set_multiplayer içinde yapılıyor (duplikasyon önlemek için)
            # self._game_controller.load(level_id)  # set_multiplayer içinde yüklenecek
            
            # Multiplayer modunu aktif et (GameScene'e client'ı ver)
            # Bu çağrı remote player pozisyonlarını da set edecek ve level'i yükleyecek
            if hasattr(self._game_scene, 'set_multiplayer'):
                self._game_scene.set_multiplayer(self._client, players, level_id)
                
                # Server'dan gelen pozisyonu set et (set_multiplayer level yükledikten sonra)
                if my_start_position and self._game_controller.player:
                    self._game_controller.player.position = my_start_position
                    print(f"✅ Local player pozisyonu server'dan ayarlandı: {my_start_position}")
                else:
                    print(f"⚠️ Local player pozisyonu ayarlanamadı! my_start_position={my_start_position}, player={self._game_controller.player}")
            
            # Oyun ekranına geç
            self._manager.switch_to(self._game_scene)
        else:
            print("⚠️ GameController veya GameScene bulunamadı!")
    
    def _on_room_deleted(self, data: dict):
        """Oda silindi callback - oyun sırasında oyuncu çıktı"""
        message = data.get("message", "Oda silindi")
        game_ended = data.get("game_ended", False)
        
        if game_ended:
            # Oyun sırasında oyuncu çıktı - menüye dön
            logger.info(f"💀 Game ended: {message}")
            # Client'ı disconnect et
            if self._client:
                self._client.disconnect()
            # Menüye dön (lobby screen'den çık)
            if self._manager:
                # Main menu'ye dön (back button gibi)
                self._handle_back()
    
    def _on_error(self, error_msg: str):
        """Hata callback"""
        self._error_message = error_msg
        self._creating_room = False  # Loading state'i kapat
        self._joining_room = False  # Loading state'i kapat
        print(f"❌ Hata: {error_msg}")
    
    def _copy_room_code(self) -> None:
        """Oda kodunu clipboard'a kopyala"""
        if not self._room_code:
            self._copy_message = "❌ Oda kodu bulunamadı!"
            self._copy_message_timer = 2.0
            print("⚠️ Oda kodu yok, kopyalanamadı!")
            return
        
        try:
            # Oda kodunu kopyala
            pyperclip.copy(self._room_code)
            self._copy_message = f"✅ Kopyalandı: {self._room_code}"
            self._copy_message_timer = 3.0  # 3 saniye göster
            print(f"📋 Oda kodu kopyalandı: {self._room_code}")
            
            # Kopyalanan kodu doğrula
            try:
                clipboard_content = pyperclip.paste()
                if clipboard_content == self._room_code:
                    print(f"✅ Kopyalama doğrulandı: {clipboard_content}")
                else:
                    print(f"⚠️ Kopyalama doğrulanamadı! Beklenen: {self._room_code}, Alınan: {clipboard_content}")
            except Exception as verify_error:
                print(f"⚠️ Kopyalama doğrulama hatası: {verify_error}")
        except Exception as e:
            self._copy_message = "❌ Kopyalama başarısız!"
            self._copy_message_timer = 2.0
            print(f"❌ Kopyalama hatası: {e}")
            import traceback
            traceback.print_exc()

