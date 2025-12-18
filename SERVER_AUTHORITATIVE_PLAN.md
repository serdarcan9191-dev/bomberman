# Server-Authoritative Game State Planı

## Şu Anki Durum (Hybrid)

### ✅ Server-Authoritative (Backend'de Yönetiliyor):
- **Oyuncu pozisyonları**: `handle_player_move()` → server collision kontrolü
- **Oyuncu canları**: `player_damage()` → server'da güncelleniyor
- **Bombalar**: `place_bomb()` → server'da timer, explosion hesaplaması
- **Duvar yıkılması**: `_handle_bomb_explosion()` → server'da BREAKABLE → EMPTY

### ❌ Client-Side (Backend'de YOK):
- **Düşman pozisyonları**: Client'ta `update_enemies()` ile güncelleniyor
- **Düşman canları**: Client'ta yönetiliyor
- **Düşman-oyuncu collision**: Client'ta kontrol ediliyor, hasar server'a bildiriliyor
- **Düşman-bomba collision**: Client'ta kontrol ediliyor

## Sorunlar

1. **Cheat/Hile Riski**: Düşman state'i client-side'da → oyuncu düşmanları manipüle edebilir
2. **Senkronizasyon Sorunları**: Her client kendi düşman state'ini tutuyor → farklı oyuncular farklı şeyler görebilir
3. **Thread-Safety Sorunları**: Client-side düşman güncellemesi ile server bombaları arasında race condition
4. **Tutarsızlık**: Bazı şeyler server'dan, bazıları client'tan → karmaşık debug

## İdeal Durum: Full Server-Authoritative

### Tüm Game State Server'da:
- ✅ Oyuncu pozisyonları → Server
- ✅ Oyuncu canları → Server
- ✅ Bombalar → Server
- ✅ Düşman pozisyonları → **Server'a taşınmalı**
- ✅ Düşman canları → **Server'a taşınmalı**
- ✅ Düşman hareketi → **Server'a taşınmalı**
- ✅ Düşman-oyuncu collision → **Server'a taşınmalı**
- ✅ Düşman-bomba collision → **Server'a taşınmalı**

### Client Sadece:
- Render (görsel çizim)
- Input gönderme (WASD, SPACE)
- Server'dan gelen state'i görselleştirme

## Implementation Planı

### 1. Backend: Enemy Model Ekle

**File: `backend/models/room.py`**

```python
@dataclass
class Enemy:
    """Düşman verisi."""
    enemy_id: str
    enemy_type: str  # "static", "chasing", "smart"
    position: tuple[int, int]
    health: int = 100
    alive: bool = True
    last_move_time: float = 0.0  # Son hareket zamanı (timer için)

@dataclass
class GameRoom:
    # ... mevcut alanlar ...
    enemies: list[Enemy] = field(default_factory=list)  # YENİ
```

### 2. Backend: Enemy Spawn Logic

**File: `backend/handlers/game_handlers.py`**

```python
def start_game(self, room_id: str) -> Optional[dict[str, Any]]:
    # ... mevcut kod ...
    
    # Düşmanları spawn et (level'den enemy_positions al)
    if room.level_data:
        enemy_positions = room.level_data.enemy_positions  # Level'den al
        room.enemies = []
        for i, (x, y) in enumerate(enemy_positions):
            enemy_type = "chasing"  # Veya level'den al
            enemy = Enemy(
                enemy_id=f"enemy_{i}",
                enemy_type=enemy_type,
                position=(x, y),
                health=100
            )
            room.enemies.append(enemy)
```

### 3. Backend: Enemy Update Logic

**File: `backend/handlers/game_handlers.py`**

```python
def update_game(self, room_id: str, delta: float) -> Optional[dict[str, Any]]:
    """Oyun state'ini güncelle (bombalar, düşmanlar, vb.)"""
    room = self.rooms.get(room_id)
    if not room or not room.started:
        return None
    
    # ... mevcut bomba update kodu ...
    
    # Düşmanları güncelle
    if room.level_data:
        for enemy in room.enemies:
            if not enemy.alive:
                continue
            
            # Düşman AI: En yakın oyuncuyu bul
            nearest_player = None
            min_distance = float('inf')
            for player in room.players:
                if player.health > 0:
                    dist = abs(player.position[0] - enemy.position[0]) + abs(player.position[1] - enemy.position[1])
                    if dist < min_distance:
                        min_distance = dist
                        nearest_player = player
            
            # Hareket timer kontrolü
            enemy.last_move_time += delta
            move_interval = 0.5  # 0.5 saniyede bir hareket
            
            if enemy.last_move_time >= move_interval and nearest_player:
                # Düşman hareket mantığı (basit pathfinding)
                new_pos = self._calculate_enemy_move(enemy, nearest_player, room)
                if new_pos:
                    enemy.position = new_pos
                    enemy.last_move_time = 0.0
            
            # Düşman-oyuncu collision kontrolü
            for player in room.players:
                if player.health > 0 and enemy.position == player.position:
                    # Hasar ver
                    player.health = max(0, player.health - 10)
                    logger.info(f"Enemy {enemy.enemy_id} hit player {player.username}, health: {player.health}")
            
            # Düşman-bomba collision kontrolü (explosion tiles)
            for bomb in room.bombs:
                if bomb.exploded and enemy.position in bomb.explosion_tiles:
                    enemy.health = max(0, enemy.health - 50)
                    if enemy.health <= 0:
                        enemy.alive = False
                        logger.info(f"Enemy {enemy.enemy_id} killed by bomb")
    
    return self.get_game_state(room_id)

def _calculate_enemy_move(self, enemy: Enemy, target_player: Player, room: GameRoom) -> Optional[tuple[int, int]]:
    """Düşman için bir sonraki pozisyonu hesapla (basit pathfinding)"""
    ex, ey = enemy.position
    tx, ty = target_player.position
    
    # Basit: Hedefe doğru en yakın geçerli tile'a git
    candidates = [
        (ex + 1, ey),  # Sağ
        (ex - 1, ey),  # Sol
        (ex, ey + 1),  # Alt
        (ex, ey - 1),  # Üst
    ]
    
    # En yakın adayı seç
    best_pos = None
    min_dist = float('inf')
    
    for nx, ny in candidates:
        if not room.level_data.can_move_to(nx, ny):
            continue
        
        # Bomba kontrolü
        for bomb in room.bombs:
            if bomb.x == nx and bomb.y == ny and not bomb.exploded:
                continue  # Bomba var, geçilemez
        
        # Diğer düşmanlar kontrolü
        for other_enemy in room.enemies:
            if other_enemy != enemy and other_enemy.alive and other_enemy.position == (nx, ny):
                continue  # Başka düşman var
        
        # En yakın pozisyonu seç
        dist = abs(nx - tx) + abs(ny - ty)
        if dist < min_dist:
            min_dist = dist
            best_pos = (nx, ny)
    
    return best_pos
```

### 4. Backend: Game State'e Enemies Ekle

**File: `backend/handlers/game_handlers.py`**

```python
def get_game_state(self, room_id: str) -> Optional[dict[str, Any]]:
    # ... mevcut kod ...
    
    # Düşmanları dict formatına çevir
    enemies_data = []
    for enemy in room.enemies:
        enemies_data.append({
            "enemy_id": enemy.enemy_id,
            "enemy_type": enemy.enemy_type,
            "position": list(enemy.position),
            "health": enemy.health,
            "alive": enemy.alive
        })
    
    return {
        "type": "game_state",
        "players": players_data,
        "bombs": bombs_data,
        "destroyed_walls": destroyed_walls,
        "enemies": enemies_data  # YENİ
    }
```

### 5. Client: Enemy State'i Server'dan Al

**File: `bomberman/view/game_scene.py`**

```python
def _on_game_state_update(self, data: dict) -> None:
    # ... mevcut kod ...
    
    # Düşmanları server state'inden senkronize et
    if self._is_multiplayer:
        server_enemies = data.get("enemies", [])
        # Client'taki düşmanları server state'ine göre güncelle
        # Veya sadece server state'ini kullan (client-side enemy logic'i kaldır)
        self._server_enemies = server_enemies

def update(self, delta: float) -> None:
    if not self._is_multiplayer:
        # Single player: Normal update (client-side enemies)
        self._controller.update(delta)
    else:
        # Multiplayer: Sadece render için state'i güncelle
        # Düşman güncellemesi YOK - server'dan geliyor
        self._state = self._controller.view_state()
```

### 6. Client: Enemy Render

**File: `bomberman/view/game_scene.py`**

```python
def draw(self, surface: pygame.Surface) -> None:
    # ... mevcut kod ...
    
    # Düşmanları çiz (server state'inden)
    if self._is_multiplayer:
        for enemy_data in self._server_enemies:
            if enemy_data.get("alive", True):
                enemy_pos = enemy_data.get("position", [0, 0])
                enemy_type = enemy_data.get("enemy_type", "chasing")
                # Render enemy
    else:
        # Single player: Client-side enemies
        for enemy in self._state.enemies:
            # Render enemy
```

## Avantajlar

1. ✅ **Cheat Önleme**: Tüm game state server'da → manipüle edilemez
2. ✅ **Tutarlılık**: Tüm oyuncular aynı düşman state'ini görür
3. ✅ **Thread-Safety**: Client-side düşman güncellemesi yok → race condition yok
4. ✅ **Basitlik**: Client sadece render yapar, logic yok
5. ✅ **Debug Kolaylığı**: Tüm logic tek yerde (server)

## Dezavantajlar

1. ⚠️ **Network Trafiği**: Her frame'de düşman pozisyonları gönderilmeli (zaten players gönderiliyor)
2. ⚠️ **Server Yükü**: Düşman AI hesaplaması server'da (ama zaten bomba logic var)
3. ⚠️ **Latency**: Düşman hareketi network gecikmesine bağlı (ama oyuncu hareketi zaten öyle)

## Sonuç

**Öneri**: Server-side düşman yönetimine geçiş yapılmalı. Bu:
- Daha güvenli
- Daha tutarlı
- Daha basit
- Mevcut thread-safety sorunlarını çözer

**Not**: Network trafiği artacak ama zaten players ve bombs gönderiliyor, enemies eklemek çok büyük bir yük değil.

