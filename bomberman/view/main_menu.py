"""
Başlangıç ekranı (main menu) Elemanlarını tanımlar.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence
import math

import pygame

from .pygame_view import ViewConfig
from .scene import Scene

ConfigColor = tuple[int, int, int]


@dataclass(frozen=True)
class MenuOption:
    """Menü seçeneklerinin görünüm ve davranış tanımı."""

    label: str
    description: str
    action: Callable[[], None]


@dataclass(frozen=True)
class MenuTheme:
    background: ConfigColor
    panel: ConfigColor
    panel_accent: ConfigColor
    accent: ConfigColor
    hover: ConfigColor
    text: ConfigColor
    title: ConfigColor

    @staticmethod
    def default() -> "MenuTheme":
        """Default theme (terminal)"""
        return MenuTheme.terminal()
    
    @staticmethod
    def terminal() -> "MenuTheme":
        """Terminal theme - PC terminal görünümü (beyaz)"""
        return MenuTheme(
            background=(0, 0, 0),              # Siyah arka plan
            panel=(20, 20, 20),                # Çok koyu gri panel
            panel_accent=(40, 40, 40),        # Koyu gri accent
            accent=(255, 255, 255),           # Beyaz (butonlar)
            hover=(200, 200, 200),            # Açık gri (hover)
            text=(255, 255, 255),             # Beyaz yazı
            title=(255, 255, 255),            # Beyaz başlık
        )
    
    @staticmethod
    def dark() -> "MenuTheme":
        """Dark theme - koyu renkler (deprecated, terminal kullan)"""
        return MenuTheme.terminal()
    
    @staticmethod
    def light() -> "MenuTheme":
        """Light theme - açık renkler (deprecated, terminal kullan)"""
        return MenuTheme.terminal()
    
    @staticmethod
    def from_string(theme_name: str) -> "MenuTheme":
        """String'den theme oluştur (her zaman terminal)"""
        return MenuTheme.terminal()


class StartScreen(Scene):
    """Oyuna başlama ekranını çizen sahne."""

    def __init__(
        self,
        config: ViewConfig,
        options: Sequence[MenuOption],
        theme: MenuTheme | None = None,
        credit_text: str = "Serdar Can",
    ) -> None:
        if not options:
            raise ValueError("StartScreen en az bir menü seçeneği gerektirir.")

        self._config = config
        self._options = list(options)
        self._theme = theme or MenuTheme.default()
        self._selected = 0
        self._credit_text = credit_text
        pygame.font.init()
        from .terminal_theme import get_terminal_font
        self._title_font = get_terminal_font(40)
        self._button_font = get_terminal_font(20)
        self._hint_font = get_terminal_font(14)
        self._credit_font = get_terminal_font(12)
        self._status_font = get_terminal_font(12)
        self._surface_size: tuple[int, int] = (config.width, config.height)
        self._panel_rect = pygame.Rect(0, 0, 0, 0)
        self._db_status: bool | None = None  # None = henüz kontrol edilmedi
        
        # Animasyon için timer'lar
        self._hover_animation = 0.0  # Buton hover animasyonu
        self._pulse_timer = 0.0  # Pulse efekti için
        self._background_offset = 0.0  # Arka plan animasyonu

    def handle_events(self, events: Sequence[pygame.event.Event]) -> None:
        rects = self._button_rects(self._panel_rect)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    self._selected = (self._selected + 1) % len(self._options)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    self._selected = (self._selected - 1) % len(self._options)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self._options[self._selected].action()
            elif event.type == pygame.MOUSEMOTION:
                for idx, rect in enumerate(rects):
                    if rect.collidepoint(event.pos):
                        self._selected = idx
                        break
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for idx, rect in enumerate(rects):
                    if rect.collidepoint(event.pos):
                        self._selected = idx
                        self._options[idx].action()
                        break

    def update(self, delta: float) -> None:
        """PostgreSQL bağlantı durumunu kontrol eder."""
        # İlk yüklemede veya her 5 saniyede bir kontrol et
        if self._db_status is None:
            self._check_db_connection()

    def draw(self, surface: pygame.Surface) -> None:
        """Butonlar, başlık ve talimatları çizer - profesyonel animasyonlar ile."""
        width, height = surface.get_size()
        self._surface_size = (width, height)
        
        # Modern gradient arka plan
        self._draw_gradient_background(surface, width, height)
        
        # Dekoratif pattern
        self._draw_background_pattern(surface, width, height)
        
        panel_rect = pygame.Rect(30, 30, width - 60, height - 60)
        self._panel_rect = panel_rect
        self._draw_panel(surface, panel_rect)
        rects = self._button_rects(panel_rect)

        for idx, (rect, option) in enumerate(zip(rects, self._options)):
            is_selected = idx == self._selected
            
            # Smooth hover animasyonu
            hover_factor = 1.0
            if is_selected:
                hover_factor = 1.0 + 0.05 * (math.sin(self._hover_animation) + 1) / 2
            
            # Modern buton çizimi
            self._draw_modern_button(surface, rect, option.label, is_selected, hover_factor)

        hint_surface = self._hint_font.render(
            "Yukarı/aşağı ok ile seçim, Enter ile onay", True, self._theme.text
        )
        hint_rect = hint_surface.get_rect(center=(width // 2, height - 40))
        surface.blit(hint_surface, hint_rect)

        self._draw_db_status(surface)
        self._draw_credit(surface)

    def _draw_gradient_background(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Modern gradient arka plan - theme'e göre"""
        bg_start = self._theme.background
        # Gradient için biraz daha koyu/açık renk
        if bg_start[0] < 128:  # Dark theme
            bg_end = tuple(max(0, c - 15) for c in bg_start)
        else:  # Light theme
            bg_end = tuple(min(255, c + 15) for c in bg_start)
        
        for y in range(height):
            ratio = y / height
            r = int(bg_start[0] + (bg_end[0] - bg_start[0]) * ratio)
            g = int(bg_start[1] + (bg_end[1] - bg_start[1]) * ratio)
            b = int(bg_start[2] + (bg_end[2] - bg_start[2]) * ratio)
            pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
    
    def _draw_background_pattern(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Dekoratif arka plan pattern - theme'e göre"""
        pattern_color = self._theme.panel_accent
        grid_size = 50
        offset = int(self._background_offset) % grid_size
        
        # Hafif grid pattern
        for x in range(-grid_size + offset, width, grid_size):
            alpha = 30  # Çok hafif
            color = tuple(int(c * alpha / 255) for c in pattern_color)
            pygame.draw.line(surface, color, (x, 0), (x, height), 1)
        for y in range(-grid_size + offset, height, grid_size):
            alpha = 30
            color = tuple(int(c * alpha / 255) for c in pattern_color)
            pygame.draw.line(surface, color, (0, y), (width, y), 1)
    
    def _draw_panel(self, surface: pygame.Surface, panel_rect: pygame.Rect) -> None:
        """Başlık ve panel arka planını çizer - theme'e göre - modern gölge efektleri ile."""
        # Panel gölgesi - modern depth
        shadow_offset = 10
        shadow_rect = panel_rect.copy()
        shadow_rect.x += shadow_offset
        shadow_rect.y += shadow_offset
        
        # Theme'e göre gölge rengi
        if self._theme.background[0] < 128:  # Dark theme
            shadow_color = tuple(max(0, c - 60) for c in self._theme.background)
        else:  # Light theme
            shadow_color = tuple(min(255, c + 60) for c in self._theme.background)
        
        # Gölge blur efekti (çoklu katman)
        for i in range(3):
            blur_rect = shadow_rect.inflate(i * 2, i * 2)
            alpha = 40 - i * 10
            shadow_surf = pygame.Surface((blur_rect.width, blur_rect.height), pygame.SRCALPHA)
            shadow_rgb = (*shadow_color, alpha)
            pygame.draw.rect(shadow_surf, shadow_rgb, shadow_surf.get_rect(), border_radius=15)
            surface.blit(shadow_surf, blur_rect)
        
        # Panel arka planı - gradient efekti
        panel_surface = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        panel_start = self._theme.panel
        panel_end = self._theme.panel_accent
        for y in range(panel_rect.height):
            ratio = y / panel_rect.height
            r = int(panel_start[0] + (panel_end[0] - panel_start[0]) * ratio)
            g = int(panel_start[1] + (panel_end[1] - panel_start[1]) * ratio)
            b = int(panel_start[2] + (panel_end[2] - panel_start[2]) * ratio)
            pygame.draw.line(panel_surface, (r, g, b), (0, y), (panel_rect.width, y))
        surface.blit(panel_surface, panel_rect)
        
        # Panel çerçevesi - modern border
        pygame.draw.rect(surface, self._theme.accent, panel_rect, width=4, border_radius=15)
        inner_rect = panel_rect.inflate(-8, -8)
        pygame.draw.rect(surface, self._theme.panel_accent, inner_rect, width=2, border_radius=12)

        # Başlık - theme title rengi - pulse efekti ile
        pulse = 1.0 + 0.05 * (math.sin(self._pulse_timer) + 1) / 2
        title_surface = self._title_font.render("Bomberman Arena", True, self._theme.title)
        title_rect = title_surface.get_rect(center=(panel_rect.centerx, panel_rect.top + 60))
        
        # Başlık gölgesi - theme'e göre (dark theme'de koyu, light theme'de açık)
        if self._theme.background[0] < 128:  # Dark theme
            shadow_color = (max(0, self._theme.background[0] - 50), 
                          max(0, self._theme.background[1] - 50), 
                          max(0, self._theme.background[2] - 50))
        else:  # Light theme
            shadow_color = (min(255, self._theme.background[0] + 50), 
                          min(255, self._theme.background[1] + 50), 
                          min(255, self._theme.background[2] + 50))
        
        # Çoklu gölge katmanları (depth efekti)
        for i in range(3):
            shadow_offset = 3 + i
            shadow_surface = self._title_font.render("Bomberman Arena", True, shadow_color)
            shadow_rect = shadow_surface.get_rect(center=(panel_rect.centerx + shadow_offset, panel_rect.top + 60 + shadow_offset))
            alpha = 100 - i * 30
            shadow_surf = pygame.Surface(shadow_surface.get_size(), pygame.SRCALPHA)
            shadow_surf.blit(shadow_surface, (0, 0))
            shadow_surf.set_alpha(alpha)
            surface.blit(shadow_surf, shadow_rect)
        
        surface.blit(title_surface, title_rect)
    
    def _draw_modern_button(
        self, 
        surface: pygame.Surface, 
        rect: pygame.Rect, 
        label: str, 
        is_selected: bool,
        hover_factor: float = 1.0
    ) -> None:
        """Modern buton çizimi - smooth animasyonlar ile"""
        # Hover efekti için rect'i büyüt
        animated_rect = rect.copy()
        if is_selected:
            scale = hover_factor
            animated_rect.width = int(rect.width * scale)
            animated_rect.height = int(rect.height * scale)
            animated_rect.center = rect.center
        
        # Buton gölgesi (seçiliyse daha belirgin)
        if is_selected:
            shadow_rect = animated_rect.copy()
            shadow_rect.x += 5
            shadow_rect.y += 5
            shadow_alpha = 80
            if self._theme.background[0] < 128:  # Dark theme
                shadow_color = tuple(max(0, c - 40) for c in self._theme.background)
            else:  # Light theme
                shadow_color = tuple(min(255, c + 40) for c in self._theme.background)
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            shadow_rgb = (*shadow_color, shadow_alpha)
            pygame.draw.rect(shadow_surf, shadow_rgb, shadow_surf.get_rect(), border_radius=12)
            surface.blit(shadow_surf, shadow_rect)
        
        # Buton arka planı - gradient
        button_surface = pygame.Surface((animated_rect.width, animated_rect.height), pygame.SRCALPHA)
        if is_selected:
            # Seçili buton - theme accent rengi ile gradient
            base_color = self._theme.accent
            # Pulse efekti
            pulse = (math.sin(self._pulse_timer) + 1) / 2
            base_color = tuple(int(c * (0.8 + 0.2 * pulse)) for c in base_color)
        else:
            # Seçili değil - theme panel rengi
            base_color = self._theme.panel
        
        # Gradient efekti
        for y in range(animated_rect.height):
            ratio = y / animated_rect.height
            if is_selected:
                r = int(base_color[0] * (0.7 + 0.3 * ratio))
                g = int(base_color[1] * (0.7 + 0.3 * ratio))
                b = int(base_color[2] * (0.7 + 0.3 * ratio))
            else:
                r = int(base_color[0] * (0.9 + 0.1 * ratio))
                g = int(base_color[1] * (0.9 + 0.1 * ratio))
                b = int(base_color[2] * (0.9 + 0.1 * ratio))
            pygame.draw.line(button_surface, (r, g, b), (0, y), (animated_rect.width, y))
        
        surface.blit(button_surface, animated_rect)
        
        # Buton border - seçiliyse glow efekti
        if is_selected:
            border_color = self._theme.hover
            border_width = 4
            # Glow efekti
            glow_rect = animated_rect.inflate(8, 8)
            glow_surf = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            glow_rgb = (*border_color, 60)
            pygame.draw.rect(glow_surf, glow_rgb, glow_surf.get_rect(), border_radius=16)
            surface.blit(glow_surf, glow_rect)
        else:
            border_color = self._theme.panel_accent
            border_width = 2
        
        pygame.draw.rect(surface, border_color, animated_rect, width=border_width, border_radius=12)
        
        # Text
        text_color = self._theme.title if is_selected else self._theme.text
        label_surface = self._button_font.render(label, True, text_color)
        label_rect = label_surface.get_rect(center=animated_rect.center)
        surface.blit(label_surface, label_rect)

    def _button_rects(self, panel_rect: pygame.Rect | None = None) -> list[pygame.Rect]:
        """Mevcut seçenekler için dikdörtgen hesaplaması."""
        panel = panel_rect or self._panel_rect
        if panel.width == 0:
            panel = pygame.Rect(0, 0, self._config.width, self._config.height)
        button_width = int(panel.width * 0.7)
        button_height = 58
        button_gap = 18
        total_height = len(self._options) * button_height + (len(self._options) - 1) * button_gap
        start_y = panel.centery - total_height // 2

        rects: list[pygame.Rect] = []
        for idx in range(len(self._options)):
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = panel.centerx
            rect.y = start_y + idx * (button_height + button_gap)
            rects.append(rect)

        return rects
    
    def _button_rects_terminal(self, width: int, height: int) -> list[pygame.Rect]:
        """Terminal stili buton pozisyonları."""
        button_width = 400
        button_height = 45
        button_gap = 15
        total_height = len(self._options) * button_height + (len(self._options) - 1) * button_gap
        start_y = height // 2 - total_height // 2 + 50

        rects: list[pygame.Rect] = []
        for idx in range(len(self._options)):
            rect = pygame.Rect(0, 0, button_width, button_height)
            rect.centerx = width // 2
            rect.y = start_y + idx * (button_height + button_gap)
            rects.append(rect)

        return rects
    
    def _draw_terminal_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        is_selected: bool
    ) -> None:
        """Terminal stili buton çizimi."""
        from .terminal_theme import draw_terminal_box, draw_terminal_text
        
        border_color = self._theme.accent if is_selected else self._theme.panel_accent
        fill_color = self._theme.panel if is_selected else self._theme.background
        draw_terminal_box(surface, rect, border_color, fill_color, 2)
        
        # Text
        text_color = self._theme.title if is_selected else self._theme.text
        draw_terminal_text(surface, label, self._button_font, text_color, rect.center, "center")

    def _draw_credit(self, surface: pygame.Surface) -> None:
        credit_surface = self._credit_font.render(self._credit_text, True, self._theme.text)
        width, height = self._surface_size
        credit_rect = credit_surface.get_rect(bottomright=(width - 16, height - 6))
        surface.blit(credit_surface, credit_rect)
    
    def _draw_credit_terminal(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Terminal stili credit çizimi."""
        from .terminal_theme import draw_terminal_text
        draw_terminal_text(surface, self._credit_text, self._credit_font, self._theme.text, (width - 20, height - 10), "right")

    def _check_db_connection(self) -> None:
        """PostgreSQL bağlantı durumunu kontrol eder."""
        try:
            from repository.level_repository_postgresql import LevelRepositoryPostgreSQL
            repo = LevelRepositoryPostgreSQL()
            # Basit bir test sorgusu - en az 1 level var mı kontrol et
            levels = list(repo.find_all())
            # Eğer level varsa bağlantı başarılı
            self._db_status = len(levels) > 0
            if self._db_status:
                print(f"[OK] PostgreSQL baglanti basarili! {len(levels)} level yuklendi.")
            else:
                print("[WARN] PostgreSQL baglanti basarili ama tablolarda veri yok!")
        except ImportError as e:
            # psycopg2 kurulu değil
            print(f"[ERROR] PostgreSQL baglanti hatasi (Import): {e}")
            self._db_status = False
        except Exception as e:
            # Diğer hatalar (bağlantı, tablo yok, vs.)
            print(f"[ERROR] PostgreSQL baglanti hatasi: {type(e).__name__}: {e}")
            self._db_status = False

    def _draw_db_status(self, surface: pygame.Surface) -> None:
        """PostgreSQL bağlantı durumunu gösterir (yeşil/kırmızı buton)."""
        if self._db_status is None:
            return  # Henüz kontrol edilmedi
        
        width, height = surface.get_size()
        self._draw_db_status_terminal(surface, width, height)
    
    def _draw_db_status_terminal(self, surface: pygame.Surface, width: int, height: int) -> None:
        """Terminal stili PostgreSQL durum gösterimi."""
        if self._db_status is None:
            return
        
        from .terminal_theme import draw_terminal_text
        
        status_color = (255, 255, 255) if self._db_status else (255, 100, 100)
        status_text = "PostgreSQL: OK" if self._db_status else "PostgreSQL: ERROR"
        draw_terminal_text(surface, status_text, self._status_font, status_color, (20, 20), "left")

    @staticmethod
    def _lerp_color(a: ConfigColor, b: ConfigColor, ratio: float) -> ConfigColor:
        return tuple(int(a[i] + (b[i] - a[i]) * ratio) for i in range(3))

