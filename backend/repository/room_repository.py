"""
Room Repository: PostgreSQL'de oda yönetimi
"""
from __future__ import annotations

import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List

from config.database import POSTGRESQL_CONNECTION_STRING
from models.room import GameRoom, Player

logger = logging.getLogger(__name__)


class RoomRepository:
    """PostgreSQL'de oda yönetimi repository."""
    
    def __init__(self):
        """Repository başlat."""
        self.connection_string = POSTGRESQL_CONNECTION_STRING
    
    def _get_connection(self):
        """PostgreSQL bağlantısı al."""
        return psycopg2.connect(self.connection_string)
    
    def create_room(self, room: GameRoom) -> bool:
        """
        Yeni oda oluştur.
        
        Args:
            room: GameRoom instance
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Room ekle
                    cur.execute("""
                        INSERT INTO rooms (room_id, room_code, level_id, level_width, level_height, started)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (room_id) DO NOTHING
                    """, (
                        room.room_id,
                        room.room_code,
                        room.level_id,
                        room.level_width,
                        room.level_height,
                        room.started
                    ))
                    
                    # Oyuncuları ekle
                    if not room.players:
                        logger.warning(f"Room {room.room_code} has no players!")
                    else:
                        logger.info(f"Adding {len(room.players)} players to room {room.room_code}")
                    
                    for player in room.players:
                        try:
                            cur.execute("""
                                INSERT INTO room_players 
                                (room_id, player_id, username, socket_id, position_x, position_y, health, ready)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (room_id, player_id) DO UPDATE
                                SET username = EXCLUDED.username,
                                    socket_id = EXCLUDED.socket_id,
                                    position_x = EXCLUDED.position_x,
                                    position_y = EXCLUDED.position_y,
                                    health = EXCLUDED.health,
                                    ready = EXCLUDED.ready
                            """, (
                                room.room_id,
                                player.player_id,
                                player.username,
                                player.socket_id,
                                player.position[0],
                                player.position[1],
                                player.health,
                                player.ready
                            ))
                            logger.debug(f"Player {player.username} ({player.player_id}) added to room {room.room_code}")
                        except Exception as player_error:
                            logger.error(f"Error adding player {player.username} to room: {player_error}", exc_info=True)
                            raise  # Re-raise to rollback transaction
                    
                    conn.commit()
                    logger.info(f"Room {room.room_code} created in database with {len(room.players)} players")
                    return True
        except Exception as e:
            logger.error(f"Error creating room: {e}", exc_info=True)
            return False
    
    def get_room_by_code(self, room_code: str) -> Optional[GameRoom]:
        """
        Oda koduna göre oda bul.
        
        Args:
            room_code: Oda kodu
            
        Returns:
            GameRoom veya None
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Room bilgisini al
                    cur.execute("""
                        SELECT room_id, room_code, level_id, level_width, level_height, started
                        FROM rooms
                        WHERE room_code = %s
                    """, (room_code.upper(),))
                    
                    room_row = cur.fetchone()
                    if not room_row:
                        return None
                    
                    # Oyuncuları al
                    cur.execute("""
                        SELECT player_id, username, socket_id, position_x, position_y, health, ready
                        FROM room_players
                        WHERE room_id = %s
                        ORDER BY joined_at
                    """, (room_row['room_id'],))
                    
                    players_data = cur.fetchall()
                    
                    # GameRoom oluştur
                    room = GameRoom(
                        room_id=room_row['room_id'],
                        room_code=room_row['room_code'],
                        level_id=room_row['level_id'],
                        level_width=room_row['level_width'],
                        level_height=room_row['level_height'],
                        started=room_row['started']
                    )
                    
                    # Oyuncuları ekle
                    for p_data in players_data:
                        player = Player(
                            player_id=p_data['player_id'],
                            username=p_data['username'],
                            socket_id=p_data['socket_id'],
                            position=(p_data['position_x'], p_data['position_y']),
                            health=p_data['health'],
                            ready=p_data['ready']
                        )
                        room.players.append(player)
                    
                    return room
        except Exception as e:
            logger.error(f"Error getting room by code: {e}", exc_info=True)
            return None
    
    def get_room_by_id(self, room_id: str) -> Optional[GameRoom]:
        """
        Room ID'ye göre oda bul.
        
        Args:
            room_id: Oda ID'si
            
        Returns:
            GameRoom veya None
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Room bilgisini al
                    cur.execute("""
                        SELECT room_id, room_code, level_id, level_width, level_height, started
                        FROM rooms
                        WHERE room_id = %s
                    """, (room_id,))
                    
                    room_row = cur.fetchone()
                    if not room_row:
                        return None
                    
                    # Oyuncuları al
                    cur.execute("""
                        SELECT player_id, username, socket_id, position_x, position_y, health, ready
                        FROM room_players
                        WHERE room_id = %s
                        ORDER BY joined_at
                    """, (room_id,))
                    
                    players_data = cur.fetchall()
                    
                    # GameRoom oluştur
                    room = GameRoom(
                        room_id=room_row['room_id'],
                        room_code=room_row['room_code'],
                        level_id=room_row['level_id'],
                        level_width=room_row['level_width'],
                        level_height=room_row['level_height'],
                        started=room_row['started']
                    )
                    
                    # Oyuncuları ekle
                    for p_data in players_data:
                        player = Player(
                            player_id=p_data['player_id'],
                            username=p_data['username'],
                            socket_id=p_data['socket_id'],
                            position=(p_data['position_x'], p_data['position_y']),
                            health=p_data['health'],
                            ready=p_data['ready']
                        )
                        room.players.append(player)
                    
                    return room
        except Exception as e:
            logger.error(f"Error getting room by id: {e}", exc_info=True)
            return None
    
    def update_room(self, room: GameRoom) -> bool:
        """
        Odayı güncelle.
        
        Args:
            room: GameRoom instance
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Room bilgisini güncelle
                    cur.execute("""
                        UPDATE rooms
                        SET level_id = %s, level_width = %s, level_height = %s, started = %s
                        WHERE room_id = %s
                    """, (
                        room.level_id,
                        room.level_width,
                        room.level_height,
                        room.started,
                        room.room_id
                    ))
                    
                    # Mevcut oyuncuları sil
                    cur.execute("DELETE FROM room_players WHERE room_id = %s", (room.room_id,))
                    
                    # Oyuncuları ekle
                    for player in room.players:
                        cur.execute("""
                            INSERT INTO room_players 
                            (room_id, player_id, username, socket_id, position_x, position_y, health, ready)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            room.room_id,
                            player.player_id,
                            player.username,
                            player.socket_id,
                            player.position[0],
                            player.position[1],
                            player.health,
                            player.ready
                        ))
                    
                    conn.commit()
                    logger.debug(f"Room {room.room_code} updated in database")
                    return True
        except Exception as e:
            logger.error(f"Error updating room: {e}", exc_info=True)
            return False
    
    def add_player_to_room(self, room_id: str, player: Player) -> bool:
        """
        Oyuncuyu odaya ekle.
        
        Args:
            room_id: Oda ID'si
            player: Player instance
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO room_players 
                        (room_id, player_id, username, socket_id, position_x, position_y, health, ready)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (room_id, player_id) DO UPDATE
                        SET username = EXCLUDED.username,
                            socket_id = EXCLUDED.socket_id,
                            position_x = EXCLUDED.position_x,
                            position_y = EXCLUDED.position_y,
                            health = EXCLUDED.health,
                            ready = EXCLUDED.ready
                    """, (
                        room_id,
                        player.player_id,
                        player.username,
                        player.socket_id,
                        player.position[0],
                        player.position[1],
                        player.health,
                        player.ready
                    ))
                    conn.commit()
                    logger.debug(f"Player {player.username} added to room {room_id}")
                    return True
        except Exception as e:
            logger.error(f"Error adding player to room: {e}", exc_info=True)
            return False
    
    def remove_player_from_room(self, room_id: str, player_id: str) -> bool:
        """
        Oyuncuyu odadan çıkar.
        
        Args:
            room_id: Oda ID'si
            player_id: Oyuncu ID'si
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM room_players
                        WHERE room_id = %s AND player_id = %s
                    """, (room_id, player_id))
                    conn.commit()
                    logger.debug(f"Player {player_id} removed from room {room_id}")
                    return True
        except Exception as e:
            logger.error(f"Error removing player from room: {e}", exc_info=True)
            return False
    
    def delete_room(self, room_id: str) -> bool:
        """
        Odayı sil - room_players tablosu da CASCADE ile otomatik temizlenir.
        
        Args:
            room_id: Oda ID'si
            
        Returns:
            bool: Başarılı mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Önce kaç oyuncu olduğunu kontrol et (log için)
                    cur.execute("SELECT COUNT(*) FROM room_players WHERE room_id = %s", (room_id,))
                    player_count = cur.fetchone()[0]
                    
                    # Odayı sil (CASCADE ile room_players da otomatik silinir)
                    cur.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
                    deleted_rows = cur.rowcount
                    
                    conn.commit()
                    
                    if deleted_rows > 0:
                        logger.info(f"Room {room_id} deleted from database (removed {player_count} players via CASCADE)")
                    else:
                        logger.warning(f"Room {room_id} not found in database")
                    
                    return deleted_rows > 0
        except Exception as e:
            logger.error(f"Error deleting room: {e}", exc_info=True)
            return False
    
    def list_active_rooms(self) -> List[GameRoom]:
        """
        Aktif odaları listele (başlamamış ve oyuncu sayısı < 2).
        BASIT SELECT - Karmaşık JOIN yok!
        
        Returns:
            GameRoom listesi
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # BASIT SELECT - Başlamamış odaları al
                    cur.execute("""
                        SELECT room_id, room_code, level_id, level_width, level_height, started
                        FROM rooms
                        WHERE started = FALSE
                        ORDER BY created_at DESC
                    """)
                    
                    rooms_data = cur.fetchall()
                    rooms = []
                    
                    for room_row in rooms_data:
                        # Her oda için oyuncu sayısını kontrol et
                        cur.execute("""
                            SELECT COUNT(*) as player_count
                            FROM room_players
                            WHERE room_id = %s
                        """, (room_row['room_id'],))
                        
                        player_count_row = cur.fetchone()
                        player_count = player_count_row['player_count'] if player_count_row else 0
                        
                        # Sadece 1 oyuncusu olan odaları ekle (dolu değil)
                        if 0 < player_count < 2:
                            # Oyuncuları al
                            cur.execute("""
                                SELECT player_id, username, socket_id, position_x, position_y, health, ready
                                FROM room_players
                                WHERE room_id = %s
                                ORDER BY joined_at
                            """, (room_row['room_id'],))
                            
                            players_data = cur.fetchall()
                            
                            # GameRoom oluştur
                            room = GameRoom(
                                room_id=room_row['room_id'],
                                room_code=room_row['room_code'],
                                level_id=room_row['level_id'],
                                level_width=room_row['level_width'],
                                level_height=room_row['level_height'],
                                started=room_row['started']
                            )
                            
                            # Oyuncuları ekle
                            for p_data in players_data:
                                player = Player(
                                    player_id=p_data['player_id'],
                                    username=p_data['username'],
                                    socket_id=p_data['socket_id'],
                                    position=(p_data['position_x'], p_data['position_y']),
                                    health=p_data['health'],
                                    ready=p_data['ready']
                                )
                                room.players.append(player)
                            
                            rooms.append(room)
                    
                    return rooms
        except Exception as e:
            logger.error(f"Error listing active rooms: {e}", exc_info=True)
            return []
    
    def room_code_exists(self, room_code: str) -> bool:
        """
        Oda kodu var mı kontrol et.
        
        Args:
            room_code: Oda kodu
            
        Returns:
            bool: Var mı?
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM rooms WHERE room_code = %s", (room_code.upper(),))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking room code: {e}", exc_info=True)
            return False

