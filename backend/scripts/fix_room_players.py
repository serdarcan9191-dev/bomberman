"""
Fix Room Players: Mevcut odalara oyuncuları ekle
Eğer room_players tablosu boşsa, bu script ile düzeltebilirsiniz.
"""
import sys
import os

# Backend dizinine ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import POSTGRESQL_CONNECTION_STRING
import psycopg2
from psycopg2.extras import RealDictCursor

def fix_room_players():
    """Mevcut odalara oyuncuları ekle (eğer yoksa)"""
    try:
        conn = psycopg2.connect(POSTGRESQL_CONNECTION_STRING)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Oyuncusu olmayan odaları bul
        cur.execute("""
            SELECT r.room_id, r.room_code
            FROM rooms r
            LEFT JOIN room_players rp ON r.room_id = rp.room_id
            WHERE rp.room_id IS NULL
            AND r.started = FALSE
        """)
        
        empty_rooms = cur.fetchall()
        print(f"Found {len(empty_rooms)} rooms without players")
        
        for room in empty_rooms:
            room_id = room['room_id']
            room_code = room['room_code']
            
            print(f"Fixing room {room_code} ({room_id})...")
            
            # Bu odaya bir dummy player ekle (socket_id yok, sadece room var)
            # Aslında bu odaları silmek daha mantıklı olabilir
            # Ama şimdilik bir placeholder player ekleyelim
            
            # Önce odayı sil (oyuncusu olmayan oda anlamsız)
            cur.execute("DELETE FROM rooms WHERE room_id = %s", (room_id,))
            print(f"  Deleted empty room {room_code}")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"✅ Fixed {len(empty_rooms)} empty rooms")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_room_players()

