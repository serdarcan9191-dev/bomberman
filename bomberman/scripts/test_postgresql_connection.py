"""
PostgreSQL Bağlantı Test Scripti
PostgreSQL (Neon) bağlantısını test eder ve bilgileri gösterir.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Proje root'unu path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print("✅ psycopg2-binary kurulu")
except ImportError:
    print("❌ psycopg2-binary kurulu değil!")
    print("   Kurulum için: pip install psycopg2-binary")
    sys.exit(1)

from config.database import POSTGRESQL_CONNECTION_STRING


def test_connection():
    """PostgreSQL bağlantısını test eder"""
    print("\n" + "="*60)
    print("PostgreSQL (Neon) Bağlantı Testi")
    print("="*60)
    
    # Connection string'i güvenli şekilde göster (şifreyi gizle)
    safe_conn_str = POSTGRESQL_CONNECTION_STRING
    if "@" in safe_conn_str:
        parts = safe_conn_str.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
            if ":" in user_pass:
                user = user_pass.split(":")[0]
                safe_conn_str = safe_conn_str.replace(user_pass, f"{user}:***")
    
    print(f"\n📡 Connection String: {safe_conn_str}")
    
    try:
        print("\n🔄 Bağlantı kuruluyor...")
        conn = psycopg2.connect(POSTGRESQL_CONNECTION_STRING)
        
        print("✅ Bağlantı başarılı!")
        
        # Veritabanı bilgileri
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\n📊 PostgreSQL Versiyonu: {version.split(',')[0]}")
        
        # Tablo kontrolü
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        print(f"\n📋 Mevcut Tablolar ({len(tables)} adet):")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Level sayısı
        cursor.execute("SELECT COUNT(*) FROM levels;")
        level_count = cursor.fetchone()[0]
        print(f"\n🎮 Level Sayısı: {level_count}")
        
        # Level örnekleri
        if level_count > 0:
            cursor.execute("SELECT id, theme, width, height FROM levels ORDER BY id LIMIT 5;")
            levels = cursor.fetchall()
            print(f"\n📝 İlk 5 Level:")
            for level in levels:
                print(f"   - {level[0]}: {level[1]} ({level[2]}x{level[3]})")
        
        # Pozisyon sayıları
        cursor.execute("SELECT position_type, COUNT(*) FROM level_positions GROUP BY position_type;")
        positions = cursor.fetchall()
        print(f"\n📍 Pozisyon Sayıları:")
        for pos_type, count in positions:
            print(f"   - {pos_type}: {count}")
        
        # Enemy spawn sayısı
        cursor.execute("SELECT COUNT(*) FROM enemy_spawns;")
        spawn_count = cursor.fetchone()[0]
        print(f"\n👾 Enemy Spawn Sayısı: {spawn_count}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Tüm testler başarılı!")
        print("="*60)
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Bağlantı hatası: {e}")
        print("\n🔍 Kontrol edilecekler:")
        print("   1. Internet bağlantısı var mı?")
        print("   2. Connection string doğru mu?")
        print("   3. Neon database aktif mi?")
        return False
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

