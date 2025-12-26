"""
Giriş (login) ekranı - Terminal teması.
UI input alır, AuthService'e doğrulama isteği gönderir, sonucu gösterir.
"""
from __future__ import annotations

import threading
from typing import Iterable

import pygame

from service.auth_service import AuthService
from .main_menu import MenuTheme
from .pygame_view import ViewConfig
from .scene import Scene
from .scene_manager import SceneManager
from .terminal_theme import get_terminal_font, draw_terminal_text, draw_terminal_box


class LoginScreen(Scene):
    def __init__(
        self,
        manager: SceneManager,
        config: ViewConfig,
        auth_service: AuthService,
        theme: MenuTheme | None = None,
        on_success: callable | None = None,
        on_register: callable | None = None,
    ) -> None:
        self._manager = manager
        self._config = config
        self._auth_service = auth_service
        self._theme = theme or MenuTheme.default()
        self._on_success = on_success
        self._on_register = on_register

        pygame.font.init()
        # Terminal monospace fontlar
        self._title_font = get_terminal_font(48)
        self._subtitle_font = get_terminal_font(20)
        self._label_font = get_terminal_font(18)
        self._input_font = get_terminal_font(20)
        self._button_font = get_terminal_font(18)
        self._hint_font = get_terminal_font(14)
        self._msg_font = get_terminal_font(16)

        self._username = ""
        self._password = ""
        self._active_field = "user"  # 'user' or 'pass'
        self._message: str = ""
        self._is_loading = False
        
        # Animasyon için timer'lar
        self._cursor_timer = 0.0
        self._loading_timer = 0.0

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            # Login sonucunu işle
            if event.type == pygame.USEREVENT and hasattr(event, 'login_result'):
                self._is_loading = False
                success, message = event.login_result
                self._message = message
                
                if success:
                    self._username = ""
                    self._password = ""
                    if self._on_success:
                        self._on_success()
                    else:
                        self._manager.return_to_menu(show_loading=True)
                return
        
        # Loading sırasında input'ları ignore et
        if self._is_loading:
            return
            
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_TAB:
                    self._toggle_active()
                    continue
                if event.key == pygame.K_RETURN:
                    self._submit()
                    continue
                if event.key == pygame.K_BACKSPACE:
                    if self._active_field == "user" and self._username:
                        self._username = self._username[:-1]
                    elif self._active_field == "pass" and self._password:
                        self._password = self._password[:-1]
                else:
                    # Karakter ekle (temel ASCII)
                    ch = event.unicode
                    if ch and ch.isprintable() and len(ch) == 1:
                        if self._active_field == "user" and len(self._username) < 24:
                            self._username += ch
                        elif self._active_field == "pass" and len(self._password) < 24:
                            self._password += ch

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                user_rect, pass_rect, login_rect, register_rect = self._layout_rects()
                if user_rect.collidepoint(mx, my):
                    self._active_field = "user"
                elif pass_rect.collidepoint(mx, my):
                    self._active_field = "pass"
                elif login_rect.collidepoint(mx, my):
                    self._submit()
                elif register_rect.collidepoint(mx, my):
                    self._register()

    def update(self, delta: float) -> None:
        # Animasyon timer'larını güncelle
        self._cursor_timer += delta * 2.0
        if self._is_loading:
            self._loading_timer += delta * 3.0

    def draw(self, surface: pygame.Surface) -> None:
        width, height = surface.get_size()
        
        # Terminal arka plan - düz siyah
        surface.fill(self._theme.background)

        # Başlık
        title_text = "GIRIS YAP"
        draw_terminal_text(surface, title_text, self._title_font, (255, 255, 255), (width // 2, 80), "center")
        
        subtitle_text = "Hesabiniza giris yapin"
        draw_terminal_text(surface, subtitle_text, self._subtitle_font, (255, 255, 255), (width // 2, 120), "center")

        # Layout'u hesapla
        user_rect, pass_rect, login_rect, register_rect = self._layout_rects()

        # Input alanları - terminal stili
        self._draw_terminal_input(
            surface, 
            user_rect, 
            "Kullanici Adi", 
            self._username, 
            active=self._active_field == "user" and not self._is_loading,
            disabled=self._is_loading
        )
        
        self._draw_terminal_input(
            surface, 
            pass_rect, 
            "Parola", 
            "*" * len(self._password), 
            active=self._active_field == "pass" and not self._is_loading,
            disabled=self._is_loading,
            is_password=True
        )

        # Giriş butonu - terminal stili
        button_text = "GIRIS YAP" if not self._is_loading else f"GIRIS YAPILIYOR{'.' * (int(self._loading_timer) % 4)}"
        self._draw_terminal_button(surface, login_rect, button_text, disabled=self._is_loading)

        # Kayıt linki - terminal stili
        register_text = "Hesabiniz yoksa kayit olun"
        draw_terminal_text(surface, register_text, self._hint_font, (255, 255, 255), register_rect.center, "center")

        # Mesaj gösterimi
        if self._message:
            msg_color = (255, 255, 255) if "basar" in self._message.lower() else (255, 100, 100)
            draw_terminal_text(surface, self._message, self._msg_font, msg_color, (width // 2, login_rect.bottom + 40), "center")

        # İpucu
        hint_text = "TAB: Alan degistir  |  ENTER: Giris  |  ESC: Geri"
        draw_terminal_text(surface, hint_text, self._hint_font, (200, 200, 200), (width // 2, height - 30), "center")


    # Yardımcılar
    def _toggle_active(self) -> None:
        self._active_field = "pass" if self._active_field == "user" else "user"

    def _submit(self) -> None:
        if self._is_loading:
            return
            
        if not self._username or not self._password:
            self._message = "⚠️ Lütfen kullanıcı adı ve parola girin"
            return
        
        # Loading state'e geç
        self._is_loading = True
        self._message = ""
        
        # Backend doğrulamasını ayrı thread'de yap
        def login_thread():
            success, message = self._auth_service.login(self._username, self._password)
            # Ana thread'e sonucu ilet
            pygame.event.post(pygame.event.Event(
                pygame.USEREVENT,
                {'login_result': (success, message)}
            ))
        
        thread = threading.Thread(target=login_thread, daemon=True)
        thread.start()

    def _register(self) -> None:
        if self._on_register:
            self._on_register()
        else:
            self._message = "⚠️ Kayıt özelliği henüz eklenmedi"

    def _layout_rects(self):
        """Layout hesaplama - terminal stili"""
        width, height = self._config.width, self._config.height

        # Terminal stili input alanları
        input_width = 400
        input_height = 40
        start_y = 200
        gap = 80  # Daha fazla boşluk

        user_rect = pygame.Rect(0, 0, input_width, input_height)
        user_rect.centerx = width // 2
        user_rect.y = start_y

        pass_rect = pygame.Rect(0, 0, input_width, input_height)
        pass_rect.centerx = width // 2
        pass_rect.y = start_y + gap

        # Buton
        button_width = 300
        button_height = 40

        login_rect = pygame.Rect(0, 0, button_width, button_height)
        login_rect.centerx = width // 2
        login_rect.y = pass_rect.bottom + 40

        register_rect = pygame.Rect(0, 0, input_width, 30)
        register_rect.centerx = width // 2
        register_rect.y = login_rect.bottom + 30

        return user_rect, pass_rect, login_rect, register_rect
    
    def _draw_terminal_input(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        value: str,
        active: bool,
        disabled: bool = False,
        is_password: bool = False
    ) -> None:
        """Terminal stili input alanı"""
        # Label - beyaz
        draw_terminal_text(surface, label, self._label_font, (255, 255, 255), (rect.left, rect.top - 25), "left")
        
        # Input kutusu
        border_color = self._theme.accent if active else self._theme.panel_accent
        fill_color = self._theme.panel if not disabled else self._theme.background
        draw_terminal_box(surface, rect, border_color, fill_color, 2)
        
        # Text - beyaz
        text_color = (255, 255, 255) if not disabled else (100, 100, 100)
        text_x = rect.left + 10
        text_y = rect.centery
        draw_terminal_text(surface, value, self._input_font, text_color, (text_x, text_y), "left")
        
        # Cursor - aktif ve yazılabilir durumda
        if active and not disabled:
            cursor_visible = int(self._cursor_timer) % 2 == 0
            if cursor_visible:
                if value:
                    text_width = self._input_font.size(value)[0]
                    cursor_x = rect.left + 10 + text_width
                else:
                    cursor_x = rect.left + 10
                pygame.draw.line(surface, self._theme.accent, (cursor_x, rect.top + 8), (cursor_x, rect.bottom - 8), 2)
    
    def _draw_terminal_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        disabled: bool = False
    ) -> None:
        """Terminal stili buton"""
        border_color = self._theme.accent if not disabled else self._theme.panel_accent
        fill_color = self._theme.panel if not disabled else self._theme.background
        draw_terminal_box(surface, rect, border_color, fill_color, 2)
        
        # Text - beyaz
        text_color = (255, 255, 255) if not disabled else (100, 100, 100)
        draw_terminal_text(surface, label, self._button_font, text_color, rect.center, "center")
