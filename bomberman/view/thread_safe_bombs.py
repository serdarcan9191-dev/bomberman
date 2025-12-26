"""
Thread-Safe Bomba Listesi: Double-Buffered yaklaşımı
Socket.IO thread'inden gelen bombalar ile Pygame main thread'i arasında senkronizasyon sağlar.
"""
from __future__ import annotations

import threading
from typing import Any


class DoubleBufferedBombs:
    """
    Double-Buffered bomba listesi - thread-safe.
    
    Socket.IO thread'i back buffer'a yazar, Pygame main thread front buffer'dan okur.
    Her frame başında buffer'lar swap edilir.
    """
    
    def __init__(self) -> None:
        """Double-buffered bomba listesi başlat."""
        self._front_buffer: list[dict[str, Any]] = []  # Main thread okur
        self._back_buffer: list[dict[str, Any]] = []   # Socket.IO thread yazar
        self._lock = threading.Lock()
    
    def swap_buffers(self) -> None:
        """
        Buffer'ları swap et - update() başında çağrılır (main thread).
        En güncel bombaları front buffer'a alır.
        """
        with self._lock:
            self._front_buffer, self._back_buffer = self._back_buffer, self._front_buffer
    
    def update(self, new_bombs: list[dict[str, Any]]) -> None:
        """
        Bomba listesini güncelle - _on_game_state_update()'de çağrılır (Socket.IO thread).
        
        Args:
            new_bombs: Server'dan gelen yeni bomba listesi
        """
        with self._lock:
            # Back buffer'a yaz (front buffer okunurken değişmez)
            self._back_buffer = [
                {
                    "x": b.get("x", 0),
                    "y": b.get("y", 0),
                    "timer": b.get("timer", 4.0),
                    "exploded": b.get("exploded", False),
                    "explosion_timer": b.get("explosion_timer", 1.0),
                    "explosion_tiles": b.get("explosion_tiles", [])
                }
                for b in new_bombs
            ]
    
    def get_bombs(self) -> list[dict[str, Any]]:
        """
        Güncel bomba listesini al - update() içinde kullanılır (main thread).
        
        Returns:
            Front buffer'daki bomba listesi (thread-safe kopya)
        """
        with self._lock:
            return self._front_buffer.copy()
    
    def get_active_bombs(self) -> list[dict[str, Any]]:
        """
        Sadece aktif (patlamamış) bombaları al.
        
        Returns:
            Patlamamış bombaların listesi
        """
        with self._lock:
            return [
                b for b in self._front_buffer
                if not b.get("exploded", False)
            ]

