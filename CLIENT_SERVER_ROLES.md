# Client-Server Rolleri (Multiplayer)

## 🎯 Temel Prensip

**Multiplayer'da Pygame client artık sadece bir RENDERER'dır!**

Tüm game logic server'da, client sadece görsel render yapar.

## 📊 Roller

### 🖥️ Server (Backend)
**TÜM Game Logic:**
- ✅ Oyuncu hareketi (collision kontrolü ile)
- ✅ Oyuncu canları (hasar hesaplama)
- ✅ Bomba yerleştirme ve timer'ları
- ✅ Bomba patlamaları (explosion tiles hesaplama)
- ✅ Duvar yıkılması (BREAKABLE → EMPTY)
- ✅ Düşman pozisyonları ve hareketi
- ✅ Düşman canları
- ✅ Düşman-oyuncu collision (hasar verme)
- ✅ Düşman-bomba collision (hasar alma)
- ✅ Tüm collision detection

**Server → Client:**
- `game_state` event'i ile tüm state gönderilir:
  - `players`: Oyuncu pozisyonları, canları
  - `bombs`: Bomba pozisyonları, timer'ları, explosion tiles
  - `destroyed_walls`: Kırılan duvarlar
  - `enemies`: Düşman pozisyonları, canları, tipleri

### 🎮 Client (Pygame)
**SADECE Render (Görsel):**
- ✅ Server'dan gelen state'i görselleştirir
- ✅ Animasyonlar (bomba patlama, hasar efektleri)
- ✅ Input gönderme (WASD → `player_move`, SPACE → `place_bomb`)
- ✅ Görsel senkronizasyon

**Client → Server:**
- `player_move`: Hareket intent'i (server collision kontrolü yapar)
- `place_bomb`: Bomba koyma intent'i (server doğrulama yapar)

## 🔄 Örnekler

### 1. Hasar Verme
```
Server:
  - Düşman oyuncuya çarptı → health -= 10
  - game_state gönderir: {"players": [{"health": 90}]}

Client:
  - Server'dan health = 90 alır
  - Sadece görsel olarak can değerini günceller
  - (Opsiyonel) Hasar efekti animasyonu gösterir
```

### 2. Duvar Kaldırma
```
Server:
  - Bomba patladı → BREAKABLE tile → EMPTY
  - game_state gönderir: {"destroyed_walls": [{"x": 5, "y": 3}]}

Client:
  - Server'dan destroyed_walls alır
  - Sadece görsel olarak duvar sprite'ını kaldırır
  - MapRenderer artık o tile'ı EMPTY olarak render eder
```

### 3. Bomba Patlama
```
Server:
  - Bomba timer <= 0 → explosion_tiles hesapla
  - game_state gönderir: {"bombs": [{"exploded": true, "explosion_tiles": [...]}]}

Client:
  - Server'dan explosion_tiles alır
  - Sadece görsel olarak patlama animasyonu gösterir
  - Explosion sprite'ını explosion_tiles pozisyonlarında render eder
```

### 4. Düşman Hareketi
```
Server:
  - Düşman AI hesaplar → yeni pozisyon
  - game_state gönderir: {"enemies": [{"position": [7, 4]}]}

Client:
  - Server'dan enemy position alır
  - Sadece görsel olarak düşman sprite'ını yeni pozisyonda render eder
```

## ✅ Avantajlar

1. **Cheat Önleme**: Tüm logic server'da → manipüle edilemez
2. **Tutarlılık**: Tüm oyuncular aynı state'i görür
3. **Basitlik**: Client kodu çok basit (sadece render)
4. **Thread-Safety**: Client-side logic yok → race condition yok
5. **Debug Kolaylığı**: Tüm logic tek yerde (server)

## 📝 Client Kodu Özeti

```python
# Multiplayer'da update() metodu:
def update(self, delta: float) -> None:
    if multiplayer:
        # Sadece buffer swap (render için)
        self._server_bombs.swap_buffers()
        # State refresh (render için)
        self._state = self._controller.view_state()
    else:
        # Single player: Normal logic
        self._controller.update(delta)

# Server'dan state geldiğinde:
def _on_game_state_update(self, data: dict) -> None:
    # Sadece state'i al ve görsel olarak güncelle
    self._server_bombs.update(data.get("bombs", []))
    self._server_enemies = data.get("enemies", [])
    # Player pozisyonları ve canları güncelle
    # Hiçbir logic yok - sadece görsel senkronizasyon!
```

## 🎨 Render Özeti

```python
def draw(self, surface: pygame.Surface) -> None:
    # Harita render (server'dan gelen destroyed_walls'a göre)
    # Oyuncular render (server'dan gelen positions'a göre)
    # Bombalar render (server'dan gelen bombs'a göre)
    # Düşmanlar render (server'dan gelen enemies'a göre)
    # Animasyonlar (explosion, hasar efektleri)
    # UI (can, bomba sayısı - server'dan gelen değerlere göre)
```

## 🚫 Client'da OLMAYAN Şeyler

- ❌ Collision detection
- ❌ Hasar hesaplama
- ❌ Bomba timer güncellemesi
- ❌ Düşman AI
- ❌ Düşman hareketi
- ❌ Duvar yıkılması logic'i
- ❌ Game state hesaplama

**Client sadece: Render + Input gönderme!**

