"""
Level Service: Level yükleme, doğrulama ve yönetimi.
Repository ve Model katmanlarını kullanarak level verilerini sağlar.
"""
from __future__ import annotations

from typing import Iterable, Optional

from model.level import LevelConfig, LevelRepository


class LevelService:
    """Level yönetimi (yükleme, listeleme, validasyon)."""

    def __init__(self) -> None:
        """Service başlatır ve level listesini hazırlar."""
        self._levels: dict[str, LevelConfig] = {}
        self._level_order: list[str] = []
        self._current_level_id: Optional[str] = None
        self._ensure_levels_loaded()

    def _ensure_levels_loaded(self) -> None:
        """Level listesini yükler (cache yapılı)."""
        if self._level_order:
            return
        configs = list(LevelRepository.list_levels())
        self._level_order = [config.id for config in configs]
        self._levels = {config.id: config for config in configs}

    def load_level(self, level_id: str) -> LevelConfig:
        """
        Level'i ID'ye göre yükler.
        
        Args:
            level_id: Yüklenecek level ID'si
            
        Returns:
            LevelConfig: Yüklenen level ayarları
            
        Raises:
            ValueError: Level bulunamadıysa
        """
        self._ensure_levels_loaded()
        level = self._levels.get(level_id)
        if level is None:
            raise ValueError(f"Level '{level_id}' bulunamadı")
        self._current_level_id = level_id
        return level

    def get_current_level_id(self) -> Optional[str]:
        """Şu an yüklenmiş level ID'sini döndürür."""
        return self._current_level_id

    def list_all_levels(self) -> list[str]:
        """Tüm level ID'lerini sırasıyla döndürür."""
        self._ensure_levels_loaded()
        return self._level_order.copy()

    def get_level_count(self) -> int:
        """Toplam level sayısını döndürür."""
        self._ensure_levels_loaded()
        return len(self._level_order)

    def get_next_level_id(self) -> Optional[str]:
        """Mevcut level'den sonraki level ID'sini döndürür."""
        if self._current_level_id is None:
            return None
        self._ensure_levels_loaded()
        try:
            index = self._level_order.index(self._current_level_id)
        except ValueError:
            return None
        if index + 1 >= len(self._level_order):
            return None
        return self._level_order[index + 1]

    def get_current_level_index(self) -> Optional[int]:
        """Şu an yüklenmiş level'in sıra numarasını döndürür (1-indexed)."""
        if self._current_level_id is None:
            return None
        self._ensure_levels_loaded()
        try:
            index = self._level_order.index(self._current_level_id)
        except ValueError:
            return None
        return index + 1

    def level_exists(self, level_id: str) -> bool:
        """Level var mı kontrol eder."""
        self._ensure_levels_loaded()
        return level_id in self._levels

    def load_next_level(self) -> bool:
        """Mevcut level'den sonraki level'i yükler."""
        next_id = self.get_next_level_id()
        if next_id is None:
            return False
        self.load_level(next_id)
        return True

    def reload_current_level(self) -> bool:
        """Şu an yüklenmiş level'i yeniden yükler."""
        if self._current_level_id is None:
            return False
        return self.load_level(self._current_level_id) is not None
