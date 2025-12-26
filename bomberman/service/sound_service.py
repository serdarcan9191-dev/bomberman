"""
Sound Service: Ses yönetimi (müzik, efektler).
Pygame mixer'ı kapsüller; view katmanından bağımsız backend.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pygame


class SoundService:
    """Oyun seslerini yönetir (müzik, efektler)."""

    def __init__(self, assets_dir: Optional[Path] = None) -> None:
        """
        Service başlatır.
        
        Args:
            assets_dir: Assets klasörünün yolu (None ise varsayılan kullanılır)
        """
        pygame.mixer.init()
        self._assets_dir = assets_dir or (Path(__file__).resolve().parent.parent / "assets")
        self._current_music: Optional[str] = None
        self._music_volume: float = 0.5
        self._sfx_volume: float = 0.7
        self._muted: bool = False

    def play_music(self, filename: str, loop: bool = True, volume: Optional[float] = None) -> bool:
        """
        Arka plan müziği çalar.
        
        Args:
            filename: Ses dosyası adı (assets/ altında)
            loop: Döngü mü? (-1 = sonsuz, 0 = bir kez)
            volume: Ses seviyesi (0.0-1.0), None = varsayılan
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            filepath = self._assets_dir / filename
            if not filepath.exists():
                return False
            
            pygame.mixer.music.load(str(filepath))
            loops = -1 if loop else 0
            pygame.mixer.music.play(loops)
            
            if volume is not None:
                self.set_music_volume(volume)
            else:
                pygame.mixer.music.set_volume(self._music_volume)
            
            self._current_music = filename
            return True
        except pygame.error:
            return False

    def stop_music(self) -> None:
        """Müziği durdurur."""
        pygame.mixer.music.stop()
        self._current_music = None

    def pause_music(self) -> None:
        """Müziği duraklatır."""
        pygame.mixer.music.pause()

    def unpause_music(self) -> None:
        """Müziği devam ettirir."""
        pygame.mixer.music.unpause()

    def set_music_volume(self, volume: float) -> None:
        """
        Müzik ses seviyesini ayarlar.
        
        Args:
            volume: 0.0 (sessiz) - 1.0 (maksimum)
        """
        self._music_volume = max(0.0, min(1.0, volume))
        if not self._muted:
            pygame.mixer.music.set_volume(self._music_volume)

    def play_sound(self, filename: str, volume: Optional[float] = None) -> Optional[pygame.mixer.Channel]:
        """
        Ses efekti çalar.
        
        Args:
            filename: Ses dosyası adı (assets/ altında)
            volume: Ses seviyesi (0.0-1.0), None = varsayılan
            
        Returns:
            Channel veya None (başarısızsa)
        """
        try:
            filepath = self._assets_dir / filename
            if not filepath.exists():
                return None
            
            sound = pygame.mixer.Sound(str(filepath))
            if volume is not None:
                sound.set_volume(max(0.0, min(1.0, volume)))
            else:
                sound.set_volume(self._sfx_volume)
            
            channel = sound.play()
            return channel
        except pygame.error:
            return None

    def set_sfx_volume(self, volume: float) -> None:
        """
        Efekt ses seviyesini ayarlar.
        
        Args:
            volume: 0.0 (sessiz) - 1.0 (maksimum)
        """
        self._sfx_volume = max(0.0, min(1.0, volume))

    def mute(self) -> None:
        """Tüm sesleri kapat."""
        self._muted = True
        pygame.mixer.music.set_volume(0.0)

    def unmute(self) -> None:
        """Tüm sesleri aç."""
        self._muted = False
        pygame.mixer.music.set_volume(self._music_volume)

    def is_music_playing(self) -> bool:
        """Müzik çalıyor mu?"""
        return pygame.mixer.music.get_busy()

    def get_current_music(self) -> Optional[str]:
        """Şu an çalan müzik dosyasını döndürür."""
        return self._current_music
