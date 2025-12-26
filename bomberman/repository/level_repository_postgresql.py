"""
Level Repository: Level verilerini PostgreSQL (Neon) ile yöneten repository.
SOLID - Repository Pattern: Veri erişim katmanını soyutlar.
"""
from __future__ import annotations

from typing import Iterable, Optional

from model.level import LevelDefinition, Theme

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import SimpleConnectionPool
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    psycopg2 = None
    RealDictCursor = None
    SimpleConnectionPool = None

from config.database import POSTGRESQL_CONNECTION_STRING


class LevelRepositoryPostgreSQL:
    """
    Level Repository: PostgreSQL (Neon) ile level verilerini yönetir.
    Repository Pattern - Veri erişim mantığını iş mantığından ayırır.
    """

    def __init__(self, connection_string: str | None = None) -> None:
        """
        Args:
            connection_string: PostgreSQL connection string (None ise config'den alır)
        """
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 kurulu değil! 'pip install psycopg2-binary' komutu ile kurun.")
        
        self._connection_string = connection_string or POSTGRESQL_CONNECTION_STRING

    def _get_connection(self):
        """Veritabanı bağlantısı oluşturur"""
        return psycopg2.connect(self._connection_string)

    def find_by_id(self, level_id: str) -> Optional[LevelDefinition]:
        """ID'ye göre level bulur"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT * FROM public.levels WHERE id = %s", (level_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            row_dict = dict(row)
            positions = self._get_positions(conn, level_id, row_dict)
            enemy_spawns = self._get_enemy_spawns(conn, level_id, row_dict)
            
            return self._map_row_to_definition(row_dict, positions, enemy_spawns)
        finally:
            conn.close()

    def find_all(self) -> Iterable[LevelDefinition]:
        """Tüm levelları getirir"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            # Public schema'dan tabloları al
            cursor.execute("SELECT * FROM public.levels ORDER BY id")
            
            for row in cursor.fetchall():
                level_id = row['id']
                row_dict = dict(row)
                positions = self._get_positions(conn, level_id, row_dict)
                enemy_spawns = self._get_enemy_spawns(conn, level_id, row_dict)
                yield self._map_row_to_definition(row_dict, positions, enemy_spawns)
        finally:
            conn.close()

    def save(self, definition: LevelDefinition) -> None:
        """Level kaydeder (INSERT veya UPDATE)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            
            # Düşman sayılarını hesapla
            static_count = sum(spawn.get("count", 0) for spawn in definition.enemy_spawns if spawn.get("type") == "STATIC")
            chasing_count = sum(spawn.get("count", 0) for spawn in definition.enemy_spawns if spawn.get("type") == "CHASING")
            smart_count = sum(spawn.get("count", 0) for spawn in definition.enemy_spawns if spawn.get("type") == "SMART")
            
            # Level kaydet (INSERT ... ON CONFLICT)
            # NOT: exit_guard ve explosion_damage local'de yönetiliyor, PostgreSQL'de saklanmıyor
            # NOT: Duvar sayıları hardcoded, PostgreSQL'de saklanmıyor
            cursor.execute("""
                INSERT INTO public.levels 
                (id, width, height, theme, player_start_x, player_start_y,
                 exit_position_x, exit_position_y, static_count, chasing_count, smart_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    width = EXCLUDED.width,
                    height = EXCLUDED.height,
                    theme = EXCLUDED.theme,
                    player_start_x = EXCLUDED.player_start_x,
                    player_start_y = EXCLUDED.player_start_y,
                    exit_position_x = EXCLUDED.exit_position_x,
                    exit_position_y = EXCLUDED.exit_position_y,
                    static_count = EXCLUDED.static_count,
                    chasing_count = EXCLUDED.chasing_count,
                    smart_count = EXCLUDED.smart_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                definition.id,
                definition.width,
                definition.height,
                definition.theme.value,
                definition.player_start[0],
                definition.player_start[1],
                definition.exit_position[0],
                definition.exit_position[1],
                static_count,
                chasing_count,
                smart_count,
            ))
            
            # NOT: Pozisyonlar artık PostgreSQL'de saklanmıyor, AVAILABLE_POSITIONS'dan hesaplanıyor
            # level_positions tablosu kullanılmıyor
            
            # NOT: enemy_spawns tablosu artık kullanılmıyor, bilgiler levels tablosunda
            
            conn.commit()
        finally:
            conn.close()

    def delete(self, level_id: str) -> bool:
        """Level siler (CASCADE ile pozisyonlar ve spawns da silinir)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM public.levels WHERE id = %s", (level_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def _get_positions(self, conn, level_id: str, row: dict) -> dict[str, list[tuple[int, int]] | tuple[int, int]]:
        """
        Basit harita oluşturma - MapGenerator kullanarak.
        Exit pozisyonu da dinamik hesaplanıyor.
        """
        from service.map_generator import MapGenerator
        
        # Düşman sayısı
        enemy_count = (
            row.get('static_count', 0) +
            row.get('chasing_count', 0) +
            row.get('smart_count', 0)
        )
        
        # Level numarası
        try:
            level_number = int(level_id.split('_')[1]) if '_' in level_id else 1
        except (ValueError, IndexError):
            level_number = 1
        
        # Pozisyonları oluştur (exit pozisyonu da dinamik hesaplanıyor)
        positions = MapGenerator.generate_positions(
            level_id=level_id,
            width=row['width'],
            height=row['height'],
            enemy_count=enemy_count,
            level_number=level_number,
            player_start=(row['player_start_x'], row['player_start_y']),
        )
        
        return positions

    def _get_enemy_spawns(self, conn, level_id: str, row: dict) -> list[dict[str, int]]:
        """Enemy spawn bilgilerini levels tablosundan oluşturur"""
        enemy_spawns = []
        if row.get('static_count', 0) > 0:
            enemy_spawns.append({'type': 'STATIC', 'count': row['static_count']})
        if row.get('chasing_count', 0) > 0:
            enemy_spawns.append({'type': 'CHASING', 'count': row['chasing_count']})
        if row.get('smart_count', 0) > 0:
            enemy_spawns.append({'type': 'SMART', 'count': row['smart_count']})
        return enemy_spawns

    def _map_row_to_definition(
        self,
        row: dict,
        positions: dict[str, list[tuple[int, int]] | tuple[int, int]],
        enemy_spawns: list[dict[str, int]],
    ) -> LevelDefinition:
        """PostgreSQL row'unu LevelDefinition'a dönüştürür"""
        # exit_guard ve explosion_damage local'de default değerlerle yönetiliyor
        # exit_position artık dinamik hesaplanıyor, PostgreSQL'den gelmiyor
        exit_pos = positions.get('exit', (row['exit_position_x'], row['exit_position_y']))
        if isinstance(exit_pos, tuple) and len(exit_pos) == 2:
            exit_position = exit_pos
        else:
            # Fallback: PostgreSQL'den al (eski sistem)
            exit_position = (row['exit_position_x'], row['exit_position_y'])
        
        return LevelDefinition(
            id=row['id'],
            width=row['width'],
            height=row['height'],
            theme=Theme(row['theme'].lower()),
            player_start=(row['player_start_x'], row['player_start_y']),
            enemy_positions=tuple(positions['enemy']),
            exit_position=exit_position,  # Dinamik hesaplanan exit pozisyonu
            breakable_positions=tuple(positions['breakable']),
            hard_positions=tuple(positions['hard']),
            extra_unbreakable=tuple(positions['extra_unbreakable']),
            exit_guard=0,  # Exit guard kaldırıldı
            enemy_spawns=tuple(enemy_spawns),
            explosion_damage=20,  # Local default değer
        )

