"""
Basit bir sahne yöneticisi: akışı kontrol eder ve menüye geri dönüş olanağı sağlar.
Tüm geçişlerde loading state gösterir.
"""
from __future__ import annotations

import threading
import time
from typing import Optional, Callable

from .scene import Scene


class SceneManager:
    def __init__(self) -> None:
        self._current: Optional[Scene] = None
        self._menu_scene: Optional[Scene] = None
        self._loading_scene: Optional[Scene] = None
        self._pending_scene: Optional[Scene] = None
        self._is_loading: bool = False
        self._loading_duration: float = 0.5  # Minimum loading süresi (saniye)

    @property
    def current(self) -> Scene:
        if self._current is None:
            raise RuntimeError("Şu anda aktif bir sahne yok.")
        return self._current

    def set_initial(self, scene: Scene) -> None:
        self._current = scene

    def register_menu(self, scene: Scene) -> None:
        self._menu_scene = scene
        self._current = scene
    
    @property
    def menu(self) -> Optional[Scene]:
        """Menü sahnesini döndürür."""
        return self._menu_scene

    def set_loading_scene(self, loading_scene: Scene) -> None:
        """Loading scene'i ayarla."""
        self._loading_scene = loading_scene

    def switch_to(self, scene: Scene, show_loading: bool = True) -> None:
        """
        Sahneyi değiştir - loading state ile.
        
        Args:
            scene: Geçilecek sahne
            show_loading: Loading gösterilsin mi (default: True)
        """
        if self._is_loading:
            return  # Zaten loading durumunda
        
        if not show_loading or self._loading_scene is None:
            # Loading yoksa direkt geçiş
            self._current = scene
            return
        
        # Loading state'e geç
        self._pending_scene = scene
        self._is_loading = True
        self._current = self._loading_scene
        
        # Loading'i başlat (async)
        def finish_loading():
            time.sleep(self._loading_duration)  # Minimum loading süresi
            self._current = self._pending_scene
            self._pending_scene = None
            self._is_loading = False
        
        thread = threading.Thread(target=finish_loading, daemon=True)
        thread.start()

    def return_to_menu(self, show_loading: bool = True) -> None:
        """
        Menüye geri dön - loading state ile.
        
        Args:
            show_loading: Loading gösterilsin mi (default: True)
        """
        if self._menu_scene:
            self.switch_to(self._menu_scene, show_loading=show_loading)

