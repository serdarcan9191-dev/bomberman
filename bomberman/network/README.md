# Network Layer - Multiplayer Implementation

## Mimari

```
Client 1 ←→ WebSocket ←→ Server ←→ WebSocket ←→ Client 2
```

## Kullanım

### Server Başlatma
```bash
python -m network.game_server
```

### Client Bağlantısı
```python
from network.game_client import GameClient

client = GameClient("ws://localhost:8765")
await client.connect()
await client.join_game("Player1")

# Callbacks
client.on_game_started(lambda data: print("Game started!"))
client.on_game_state(lambda data: update_ui(data))
```

## Mesaj Protokolü

### Client → Server

**JOIN_GAME**
```json
{
  "type": "join_game",
  "username": "Player1"
}
```

**PLAYER_MOVE**
```json
{
  "type": "player_move",
  "direction": "up"  // "up", "down", "left", "right"
}
```

**PLACE_BOMB**
```json
{
  "type": "place_bomb"
}
```

**LEAVE_GAME**
```json
{
  "type": "leave_game"
}
```

### Server → Client

**PLAYER_JOINED**
```json
{
  "type": "player_joined",
  "player_id": "uuid",
  "username": "Player1",
  "player_count": 1
}
```

**GAME_STARTED**
```json
{
  "type": "game_started",
  "level_id": "level_1",
  "players": [
    {"player_id": "uuid1", "username": "Player1", "position": [1, 1]},
    {"player_id": "uuid2", "username": "Player2", "position": [9, 7]}
  ]
}
```

**GAME_STATE**
```json
{
  "type": "game_state",
  "players": [
    {"player_id": "uuid1", "position": [2, 3], "health": 80},
    {"player_id": "uuid2", "position": [5, 4], "health": 100}
  ]
}
```

**ERROR**
```json
{
  "type": "error",
  "message": "Room is full"
}
```

## Bağımlılıklar

```bash
pip install websockets
```

## TODO

- [ ] GameController'ı multiplayer'a adapte et
- [ ] Client input'larını server'a ilet
- [ ] Server game logic'i ekle
- [ ] Bomb synchronization
- [ ] Enemy synchronization
- [ ] Disconnect handling
