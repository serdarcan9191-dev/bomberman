"""
Database Configuration: Veritabanı bağlantı bilgileri
"""
from __future__ import annotations

import os
from pathlib import Path

# PostgreSQL (Neon) Connection String
POSTGRESQL_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_oNmQ3KScRy4W@ep-sparkling-block-ae8t7xqr-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# SQLite (fallback)
SQLITE_DB_PATH = Path(__file__).parent.parent / "sql" / "bomberman.db"

