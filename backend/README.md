# Bomberman Multiplayer Server

Socket.io tabanlı multiplayer server. Port 7777'de çalışır.

## Kurulum

```bash
pip install -r requirements.txt
```

## Çalıştırma

```bash
python server.py
```

Server `0.0.0.0:7777` adresinde başlar.

## Socket.io Events

### Client → Server

#### `create_room`
Yeni oda oluştur.

```json
{
  "username": "Player1"
}
```

**Response:**
```json
{
  "type": "room_created",
  "room_code": "ABC123",
  "room_id": "uuid",
  "player_id": "uuid",
  "player_count": 1
}
```

#### `join_room`
Odaya katıl.

```json
{
  "username": "Player2",
  "room_code": "ABC123"
}
```

**Response:**
```json
{
  "type": "player_joined",
  "player_id": "uuid",
  "username": "Player2",
  "room_code": "ABC123",
  "player_count": 2
}
```

#### `player_move`
Oyuncu hareket.

```json
{
  "direction": "up"  // "up", "down", "left", "right"
}
```

#### `place_bomb`
Bomba koy.

```json
{}
```

#### `leave_room`
Odadan çık.

```json
{}
```

### Server → Client

#### `player_joined`
Başka bir oyuncu odaya katıldı.

```json
{
  "type": "player_joined",
  "player_id": "uuid",
  "username": "Player2",
  "room_code": "ABC123",
  "player_count": 2
}
```

#### `game_started`
Oyun başladı (oda dolu olduğunda).

```json
{
  "type": "game_started",
  "level_id": "level_1",
  "players": [
    {
      "player_id": "uuid1",
      "username": "Player1",
      "position": [1, 1],
      "health": 100,
      "ready": false
    },
    {
      "player_id": "uuid2",
      "username": "Player2",
      "position": [9, 7],
      "health": 100,
      "ready": false
    }
  ]
}
```

#### `game_state`
Oyun state güncellemesi.

```json
{
  "type": "game_state",
  "players": [
    {
      "player_id": "uuid1",
      "username": "Player1",
      "position": [2, 3],
      "health": 80,
      "ready": false
    }
  ]
}
```

#### `player_left`
Oyuncu odadan çıktı.

```json
{
  "type": "player_left",
  "player_id": "uuid",
  "player_count": 1
}
```

#### `error`
Hata mesajı.

```json
{
  "type": "error",
  "message": "Oda dolu"
}
```

## PostgreSQL

PostgreSQL bağlantısı `config/database.py` dosyasında yapılandırılmıştır. Bomberman'daki aynı connection string kullanılır.

