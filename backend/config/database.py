"""
Database Configuration: PostgreSQL bağlantı bilgileri
Bomberman'daki aynı connection string'i kullanıyoruz
"""
from __future__ import annotations

import os

# PostgreSQL (Neon) Connection String
# Bomberman'daki config/database.py'den aynı connection string
POSTGRESQL_CONNECTION_STRING = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_oNmQ3KScRy4W@ep-sparkling-block-ae8t7xqr-pooler.c-2.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

