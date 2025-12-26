"""
Auth Service: Kullanıcı kaydı ve giriş mantığını yönetir.
View katmanından bağımsız; backend işlemleri controller olarak davranır.
PostgreSQL veya bellek depolama kullanabilir.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

try:
    import psycopg2
    from psycopg2 import pool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


class AuthService:
    """Kullanıcı kimlik doğrulama ve kaydı yönetir."""

    def __init__(self, db_connection_string: Optional[str] = None) -> None:
        """
        Service başlatır.
        
        Args:
            db_connection_string: PostgreSQL bağlantı stringi (None = bellek depolama)
        """
        self._db_pool: Optional[pool.SimpleConnectionPool] = None
        self._use_postgres = False
        self._users: dict[str, str] = {}  # Fallback bellek depolama
        self._current_user_id: Optional[UUID] = None  # Giriş yapmış kullanıcının ID'si
        self._current_username: Optional[str] = None  # Giriş yapmış kullanıcının adı

        if db_connection_string and HAS_PSYCOPG2:
            try:
                self._db_pool = pool.SimpleConnectionPool(1, 5, db_connection_string)
                self._use_postgres = True
            except Exception:
                # Bağlantı başarısız → bellek depolama kullan
                self._use_postgres = False
                self._db_pool = None

    def register(self, username: str, password: str, password_confirm: str) -> tuple[bool, str]:
        """
        Yeni kullanıcı kaydı.
        
        Returns:
            (success: bool, message: str)
        """
        if not username or not password:
            return False, "Kullanıcı adı ve parola boş olamaz"
        
        if len(username) < 3:
            return False, "Kullanıcı adı en az 3 karakter olmalı"
        
        if len(password) < 6:
            return False, "Parola en az 6 karakter olmalı"
        
        if password != password_confirm:
            return False, "Parola eşleşmiyor"
        
        if self.user_exists(username):
            return False, "Bu kullanıcı adı zaten var"
        
        if self._use_postgres:
            return self._register_postgres(username, password)
        else:
            return self._register_memory(username, password)

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        Kullanıcı girişi.
        
        Returns:
            (success: bool, message: str)
        """
        if not username or not password:
            return False, "Kullanıcı adı ve parola boş olamaz"
        
        if self._use_postgres:
            return self._login_postgres(username, password)
        else:
            return self._login_memory(username, password)

    def user_exists(self, username: str) -> bool:
        """Kullanıcı var mı kontrol et."""
        if self._use_postgres:
            return self._user_exists_postgres(username)
        else:
            return username in self._users

    def _register_memory(self, username: str, password: str) -> tuple[bool, str]:
        """Bellek depolama ile kayıt."""
        self._users[username] = password
        return True, "Kayıt başarılı"

    def _login_memory(self, username: str, password: str) -> tuple[bool, str]:
        """Bellek depolama ile giriş."""
        if username not in self._users:
            return False, "Kullanıcı bulunamadı"
        
        if self._users[username] != password:
            return False, "Yanlış parola"
        
        return True, "Giriş başarılı"

    def _register_postgres(self, username: str, password: str) -> tuple[bool, str]:
        """PostgreSQL ile kayıt."""
        if not self._db_pool:
            return False, "Veritabanı bağlantısı kurulamadı"
        
        # Parolayı hash'le
        if HAS_BCRYPT:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            password_hash = password
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Yeni kullanıcıya default theme (dark) ile kayıt yap
            cursor.execute(
                "INSERT INTO public.users (user_name, user_pw, preferred_theme) VALUES (%s, %s, %s)",
                (username, password_hash, "dark")
            )
            conn.commit()
            return True, "Kayıt başarılı"
        except Exception as e:
            return False, f"Kayıt hatası: {str(e)}"
        finally:
            cursor.close()
            if conn:
                self._db_pool.putconn(conn)

    def _login_postgres(self, username: str, password: str) -> tuple[bool, str]:
        """PostgreSQL ile giriş."""
        if not self._db_pool:
            return False, "Veritabanı bağlantısı kurulamadı"
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, user_pw FROM public.users WHERE user_name = %s",
                (username,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return False, "Kullanıcı bulunamadı"
            
            user_id, stored_password_hash = result
            
            # Parolayı kontrol et
            if HAS_BCRYPT:
                if not bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
                    return False, "Yanlış parola"
            else:
                if stored_password_hash != password:
                    return False, "Yanlış parola"
            
            # Başarılı giriş: kullanıcı bilgilerini kaydet
            self._current_user_id = UUID(user_id)
            self._current_username = username
            
            return True, "Giriş başarılı"
        except Exception as e:
            return False, f"Giriş hatası: {str(e)}"
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def _user_exists_postgres(self, username: str) -> bool:
        """PostgreSQL'de kullanıcı var mı kontrol et."""
        if not self._db_pool:
            return False
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM public.users WHERE user_name = %s", (username,))
            result = cursor.fetchone()
            cursor.close()
            return result is not None
        except Exception as e:
            # Exception olursa kullanıcı yok varsay (kayıt yapılabilsin)
            print(f"[DEBUG] user_exists hatası: {e}")
            return False
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_current_user_id(self) -> Optional[UUID]:
        """Giriş yapmış kullanıcının ID'sini döndürür."""
        return self._current_user_id
    
    def get_current_username(self) -> Optional[str]:
        """Giriş yapmış kullanıcının adını döndürür."""
        return self._current_username
    
    def get_user_preferred_theme(self) -> str:
        """Kullanıcının tercih ettiği theme'i döndürür ('dark' veya 'light')."""
        if not self._current_user_id or not self._use_postgres:
            return "dark"  # Default
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT preferred_theme FROM public.users WHERE user_id = %s",
                (str(self._current_user_id),)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                return result[0]
            return "dark"  # Default
        except Exception as e:
            print(f"[DEBUG] get_user_preferred_theme hatası: {e}")
            return "dark"  # Default
        finally:
            if conn:
                self._db_pool.putconn(conn)
    
    def set_user_preferred_theme(self, theme: str) -> bool:
        """Kullanıcının tercih ettiği theme'i kaydeder ('dark' veya 'light')."""
        if not self._current_user_id or not self._use_postgres:
            return False
        
        if theme not in ("dark", "light"):
            return False
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE public.users SET preferred_theme = %s WHERE user_id = %s",
                (theme, str(self._current_user_id))
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"[DEBUG] set_user_preferred_theme hatası: {e}")
            return False
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def close(self) -> None:
        """Veritabanı bağlantılarını kapat."""
        if self._db_pool:
            self._db_pool.closeall()
