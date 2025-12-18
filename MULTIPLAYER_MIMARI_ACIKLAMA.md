# Multiplayer Mimari Açıklaması

## Genel Mimari

### 1. **Server-Authoritative (Sunucu Otoritesi) Yaklaşımı**

**Neden?**
- Cheat/hile önleme
- Tüm oyuncuların aynı oyun durumunu görmesi
- Tutarlı collision detection

**Ne Server'da?**
- ✅ **Oyuncu hareketi**: Tüm hareketler server'da kontrol edilir
- ✅ **Bomba yerleştirme**: Server'da doğrulanır ve saklanır
- ✅ **Bomba patlamaları**: Server'da hesaplanır (timer, explosion tiles)
- ✅ **Duvar yıkılması**: Server'da BREAKABLE → EMPTY dönüşümü
- ✅ **Oyuncu hasarı**: Bomba patlamalarından gelen hasar server'da
- ✅ **Collision detection**: Oyuncular için server'da kontrol edilir

**Ne Client'ta?**
- ✅ **Düşman yönetimi**: Backend'de düşman yok, client-side'da
- ✅ **Düşman hareketi**: Client'ta `update_enemies()` ile
- ✅ **Düşman-oyuncu collision**: Client'ta kontrol edilir, hasar server'a bildirilir
- ✅ **Görsel render**: Tüm görseller client-side'da

## Veri Akışı

### Oyuncu Hareketi:
```
Client (WASD tuşu) 
  → Socket.IO "player_move" event
  → Server handle_player_move()
  → Server collision kontrolü (duvarlar, bombalar, oyuncular)
  → Server pozisyonu günceller
  → Server "game_state" event gönderir
  → Client _on_game_state_update() alır
  → Client görseli günceller
```

### Bomba Yerleştirme:
```
Client (SPACE tuşu)
  → Socket.IO "place_bomb" event
  → Server handle_place_bomb()
  → Server bombayı room.bombs listesine ekler
  → Server "game_state" event gönderir (bomba bilgisi ile)
  → Client _on_game_state_update() alır
  → Client _server_bombs listesine ekler
  → Client görseli render eder
```

### Bomba Patlaması:
```
Server game_loop() (her 0.033 saniyede)
  → update_game() çağrılır
  → Bomb timer'ları azalır
  → Timer <= 0 ise _handle_bomb_explosion() çağrılır
  → Explosion tiles hesaplanır
  → BREAKABLE duvarlar EMPTY'e çevrilir
  → Oyunculara hasar verilir
  → "game_state" event gönderilir (destroyed_walls, bombs, players)
  → Client _on_game_state_update() alır
  → Client destroyed_walls'u işler
  → Client düşmanlara hasar verir (client-side)
```

## Sorun: Düşmanlar Bombalardan Geçiyor

### Mevcut Durum:
1. **Server bombaları**: `_server_bombs` listesinde tutuluyor
2. **Blocked positions**: `_update_blocked_positions()` ile güncelleniyor
3. **Timing sorunu**: `update()` metodunda sıralama:
   - ✅ `_update_blocked_positions()` ÖNCE çağrılıyor (düzeltildi)
   - ✅ `update_enemies()` SONRA çağrılıyor
   - ✅ `enemy_tile_type_at()` `_blocked_positions` kontrol ediyor

### Olası Sorunlar:

1. **Server bombaları geçici olarak ekleniyor ama timing sorunu var**
   - `_update_blocked_positions()` her frame'de çağrılıyor
   - Ama `_server_bombs` sadece `_on_game_state_update()` ile güncelleniyor
   - Eğer `update()` `_on_game_state_update()`'den ÖNCE çağrılırsa, eski bombalar kullanılıyor

2. **Odayı oluşturan oyuncu için özel durum**
   - Host oyuncu da aynı client kodunu kullanıyor
   - Ama belki server bombaları host için farklı geliyor?

## Çözüm Önerileri

### 1. Blocked Positions'ı Her Frame'de Güncelle
- `update()` metodunda `_server_bombs` her zaman güncel olmalı
- `_on_game_state_update()` ile `update()` arasında senkronizasyon sorunu olabilir

### 2. Düşman Hareketi İçin Ek Kontrol
- `enemy_tile_type_at()` içinde server bombalarını da kontrol et
- `_server_bombs` listesini direkt kontrol et (sadece `_blocked_positions` değil)

### 3. Server'da Düşman Yönetimi (Uzun Vadeli)
- Düşmanları da server'da yönet
- Client sadece görsel render yapsın
- Bu daha tutarlı olur ama daha fazla network trafiği gerektirir

## Mevcut Kod Yapısı

### Client (game_scene.py):
```python
def update(self, delta):
    if multiplayer:
        # 1. Blocked positions güncelle (server bombalarını ekle)
        _update_blocked_positions()  # Server bombaları geçici ekleniyor
        
        # 2. Düşmanları güncelle
        update_enemies(delta)  # enemy_tile_type_at() _blocked_positions kullanıyor
        
        # 3. Collision kontrolü
        _check_player_enemy_collision_multiplayer()
```

### Server (game_handlers.py):
```python
def handle_player_move():
    # 1. Tile collision
    # 2. Bomba collision
    # 3. Player collision
    # 4. Pozisyonu güncelle
    # 5. game_state döndür
```

## Sorunun Kök Nedeni

**Kesin neden**: `_server_bombs` güncellemesi ile `update()` çağrısı arasında race condition var. 

- `_on_game_state_update()` async callback (Socket.IO thread'inde - `threading.Thread`)
- `update()` main game loop'unda (Pygame main thread'inde)
- İkisi arasında thread-safety sorunu var

**Uygulanan Çözüm**: **Double-Buffered Thread-Safe Bomba Listesi**

1. **`DoubleBufferedBombs` sınıfı** oluşturuldu (`bomberman/view/thread_safe_bombs.py`)
   - `_front_buffer`: Main thread okur (Pygame)
   - `_back_buffer`: Socket.IO thread yazar
   - `threading.Lock()` ile korunuyor

2. **Buffer Swap Mekanizması**:
   - Her `update()` başında `swap_buffers()` çağrılıyor
   - Socket.IO thread back buffer'a yazıyor
   - Main thread front buffer'dan okuyor
   - Swap atomik (lock ile korunuyor)

3. **`enemy_tile_type_at()` içinde direkt kontrol**:
   - `_server_bombs_for_enemies` listesi controller'a geçiriliyor
   - Her frame'de güncel bombalar kontrol ediliyor
   - Timing sorunu çözüldü

**Sonuç**: Thread-safety sorunu çözüldü, düşmanlar artık bombalardan geçemiyor.

