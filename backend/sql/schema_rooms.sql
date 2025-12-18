-- Rooms Table Schema
-- Multiplayer oda yönetimi için PostgreSQL tablosu

CREATE TABLE IF NOT EXISTS rooms (
    room_id VARCHAR(36) PRIMARY KEY,
    room_code VARCHAR(6) UNIQUE NOT NULL,
    level_id VARCHAR(50) NOT NULL DEFAULT 'level_1',
    level_width INTEGER NOT NULL DEFAULT 11,
    level_height INTEGER NOT NULL DEFAULT 9,
    started BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Room Players Table (Many-to-Many)
CREATE TABLE IF NOT EXISTS room_players (
    id SERIAL PRIMARY KEY,
    room_id VARCHAR(36) NOT NULL REFERENCES rooms(room_id) ON DELETE CASCADE,
    player_id VARCHAR(36) NOT NULL,
    username VARCHAR(100) NOT NULL,
    socket_id VARCHAR(100) NOT NULL,
    position_x INTEGER NOT NULL DEFAULT 1,
    position_y INTEGER NOT NULL DEFAULT 1,
    health INTEGER NOT NULL DEFAULT 100,
    ready BOOLEAN NOT NULL DEFAULT FALSE,
    joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(room_id, player_id),
    UNIQUE(room_id, socket_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_rooms_room_code ON rooms(room_code);
CREATE INDEX IF NOT EXISTS idx_rooms_started ON rooms(started);
CREATE INDEX IF NOT EXISTS idx_room_players_room_id ON room_players(room_id);
CREATE INDEX IF NOT EXISTS idx_room_players_socket_id ON room_players(socket_id);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_rooms_updated_at BEFORE UPDATE ON rooms
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

