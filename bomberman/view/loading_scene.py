"""
Loading Scene: Tüm view geçişlerinde gösterilen terminal loading ekranı
"""
from __future__ import annotations

from typing import Callable, Iterable, Optional

import pygame

from view.main_menu import MenuTheme
from view.scene import Scene
from view.terminal_theme import get_terminal_font, draw_terminal_text


class LoadingScene(Scene):
    """Modern loading ekranı - view geçişlerinde gösterilir"""

    def __init__(self, on_loaded: Optional[Callable[[], None]] = None, theme: Optional[MenuTheme] = None) -> None:
        """
        Args:
            on_loaded: Yükleme tamamlandığında çağrılacak callback (opsiyonel)
            theme: MenuTheme (opsiyonel, default kullanılır)
        """
        self._on_loaded = on_loaded
        self._loading_time = 0.0
        self._message: str = "Yukleniyor"
        self._theme = theme or MenuTheme.default()
        
        pygame.font.init()
        self._title_font = get_terminal_font(40)
        self._loading_font = get_terminal_font(20)
        self._message_font = get_terminal_font(16)
    
    def set_on_loaded(self, callback: Optional[Callable[[], None]]) -> None:
        """Callback'i set eder ve loading state'i resetler"""
        self._on_loaded = callback
        self._loading_time = 0.0
    
    def set_message(self, message: str) -> None:
        """Loading mesajını ayarla"""
        self._message = message

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        """Loading ekranında event handling yok"""
        pass

    def update(self, delta: float) -> None:
        """Loading animasyonu"""
        self._loading_time += delta
        
        # Eğer callback varsa ve minimum süre geçtiyse çağır
        if self._on_loaded and self._loading_time >= 0.3:
            callback = self._on_loaded
            self._on_loaded = None  # Tekrar çağrılmasını önle
            callback()

    def draw(self, surface: pygame.Surface) -> None:
        """Terminal loading ekranını çizer"""
        width, height = surface.get_size()
        
        # Terminal arka plan - düz siyah
        surface.fill(self._theme.background)
        
        # Başlık
        title_text = "BOMBERMAN"
        draw_terminal_text(surface, title_text, self._title_font, self._theme.title, (width // 2, height // 2 - 60), "center")
        
        # Loading mesajı
        dots = "." * (int(self._loading_time * 2) % 4)
        loading_text = f"{self._message}{dots}"
        draw_terminal_text(surface, loading_text, self._loading_font, self._theme.text, (width // 2, height // 2), "center")
        
        # Terminal stili spinner - basit çizgi
        spinner_y = height // 2 + 40
        spinner_width = 200
        spinner_x = width // 2 - spinner_width // 2
        
        # Progress bar stili
        progress = (self._loading_time * 0.5) % 1.0
        bar_width = int(spinner_width * progress)
        bar_rect = pygame.Rect(spinner_x, spinner_y, bar_width, 4)
        pygame.draw.rect(surface, self._theme.accent, bar_rect)
        
        # Border
        full_rect = pygame.Rect(spinner_x, spinner_y, spinner_width, 4)
        pygame.draw.rect(surface, self._theme.panel_accent, full_rect, width=1)

