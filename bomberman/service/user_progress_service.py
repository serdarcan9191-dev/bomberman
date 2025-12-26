"""
User Progress Service: Kullanıcı ilerleme takibi (PostgreSQL).
Kullanıcıların hangi levelde olduğunu kaydeder ve yükler.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)


class UserProgressService:
    """Kullanıcı ilerleme durumu yönetimi (PostgreSQL)."""

    def __init__(self, db_connection_string: str | None = None) -> None:
        """
        Service'i başlatır.
        
        Args:
            db_connection_string: PostgreSQL bağlantı dizesi (Neon için)
        """
        self._db_connection_string = db_connection_string
        self._connection_pool: pool.SimpleConnectionPool | None = None
        
        if db_connection_string:
            try:
                # Connection pool oluştur (min=1, max=5)
                self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 5, db_connection_string
                )
                logger.info("UserProgressService: PostgreSQL connection pool created")
            except Exception as e:
                logger.error(f"UserProgressService: PostgreSQL connection failed: {e}")
                self._connection_pool = None

    def get_current_level(self, user_id: UUID) -> str | None:
        """
        Kullanıcının mevcut levelini getirir.
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            str | None: Level ID (örn: 'level_1') veya None
        """
        if not self._connection_pool:
            return None
        
        conn = None
        try:
            conn = self._connection_pool.getconn()
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT current_level FROM public.user_progress WHERE user_id = %s",
                (str(user_id),)
            )
            result = cursor.fetchone()
            cursor.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"get_current_level failed: {e}")
            return None
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def save_progress(self, user_id: UUID, current_level: str) -> bool:
        """
        Kullanıcının levelini kaydeder (INSERT veya UPDATE).
        
        Args:
            user_id: Kullanıcı ID'si
            current_level: Mevcut level ID'si (örn: 'level_2')
            
        Returns:
            bool: Başarılı ise True
        """
        if not self._connection_pool:
            return False
        
        conn = None
        try:
            conn = self._connection_pool.getconn()
            cursor = conn.cursor()
            
            # UPSERT (ON CONFLICT DO UPDATE)
            cursor.execute(
                """
                INSERT INTO public.user_progress (user_id, current_level)
                VALUES (%s, %s)
                ON CONFLICT (user_id)
                DO UPDATE SET 
                    current_level = EXCLUDED.current_level,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (str(user_id), current_level)
            )
            
            conn.commit()
            cursor.close()
            logger.info(f"Progress saved: user={user_id}, level={current_level}")
            return True
            
        except Exception as e:
            logger.error(f"save_progress failed: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                self._connection_pool.putconn(conn)

    def reset_progress(self, user_id: UUID) -> bool:
        """
        Kullanıcının ilerlemesini sıfırlar (level_1'e döndürür).
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        return self.save_progress(user_id, "level_1")

    def has_progress(self, user_id: UUID) -> bool:
        """
        Kullanıcının kayıtlı bir ilerlemesi var mı kontrol eder.
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            bool: İlerleme varsa True
        """
        current_level = self.get_current_level(user_id)
        return current_level is not None

    def __del__(self):
        """Connection pool'u temizle."""
        if self._connection_pool:
            self._connection_pool.closeall()
