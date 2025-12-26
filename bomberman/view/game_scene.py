"""
Oyun sahnesi: controller'dan level ve oyuncu pozisyonlarını çizer.
"""
from __future__ import annotations

import logging
from typing import Callable, Iterable, Optional

import pygame

from controller.game_controller import GameController
from model.enemy import EnemyType
from service.sound_service import SoundService
from view.characters import CharacterSprite, CharacterFactory, load_asset_image
from view.effects import load_effect_image
from view.map_renderer import MapRenderer
from view.scene import Scene

logger = logging.getLogger(__name__)


class GameScene(Scene):

    def __init__(
        self,
        controller: GameController,
        sound_service: SoundService,
        exit_callback: Callable[[], None] | None = None,
    ) -> None:
        self._controller = controller
        self._sound_service = sound_service
        self._renderer = MapRenderer()
        roster = CharacterFactory.roster()
        self._player_sprite = CharacterSprite(roster[0]) if roster else None
        self._bomb_image = load_effect_image("bomb.png")
        self._explosion_image = load_effect_image("Explosion.png")
        self._next_button_rect: pygame.Rect | None = None
        self._restart_button_rect: pygame.Rect | None = None
        self._exit_callback = exit_callback
        self._exit_button_rect: pygame.Rect | None = None
        self._enemy_images = {
            EnemyType.STATIC: load_asset_image("chenemy.png"),
            EnemyType.CHASING: load_asset_image("senemy.png"),
            EnemyType.SMART: load_asset_image("ienemy.png"),
        }
        self._state = self._controller.view_state()
        
        # Multiplayer support
        self._multiplayer_client: Optional[object] = None  # SocketIOClient
        self._remote_players: dict[str, dict] = {}  # player_id -> player data
        self._is_multiplayer: bool = False
        self._my_player_id: Optional[str] = None
        # Thread-safe double-buffered bomba listesi
        from view.thread_safe_bombs import DoubleBufferedBombs
        self._server_bombs: DoubleBufferedBombs = DoubleBufferedBombs()
        self._server_enemies: list[dict] = []  # Server'dan gelen düşmanlar (Server-authoritative)
        self._processed_destroyed_walls: set[tuple[int, int]] = set()  # İşlenmiş destroyed walls (tekrar işleme önlemek için)
        self._exit_reached_logged: bool = False  # Exit'e ulaşma log'unun sadece bir kez yazılması için

    def handle_events(self, events: Iterable[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self._state.dead:
                    continue
                if event.key == pygame.K_w:
                    if self._is_multiplayer and self._multiplayer_client:
                        # Multiplayer: Sadece server'a gönder, client hareket etmez
                        self._multiplayer_client.send_move("up")
                    else:
                        # Single player: Local hareket
                        self._controller.move_player(0, -1)
                elif event.key == pygame.K_s:
                    if self._is_multiplayer and self._multiplayer_client:
                        self._multiplayer_client.send_move("down")
                    else:
                        self._controller.move_player(0, 1)
                elif event.key == pygame.K_a:
                    if self._is_multiplayer and self._multiplayer_client:
                        self._multiplayer_client.send_move("left")
                    else:
                        self._controller.move_player(-1, 0)
                elif event.key == pygame.K_d:
                    if self._is_multiplayer and self._multiplayer_client:
                        self._multiplayer_client.send_move("right")
                    else:
                        self._controller.move_player(1, 0)
                elif event.key == pygame.K_SPACE:
                    if self._is_multiplayer and self._multiplayer_client:
                        # Multiplayer: Sadece server'a gönder (limit yok)
                        self._multiplayer_client.send_place_bomb()
                    else:
                        # Single player: Local bomba
                        prev_active = sum(1 for b in self._state.bombs if not b.exploded)
                        self._controller.place_bomb()
                        self._state = self._controller.view_state()
                        new_active = sum(1 for b in self._state.bombs if not b.exploded)
                        if new_active > prev_active:
                            self._play_primed_sound()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if (
                    self._exit_button_rect
                    and self._exit_button_rect.collidepoint(event.pos)
                    and self._exit_callback
                ):
                    # Multiplayer'dan çıkıyorsak state'i temizle
                    if self._is_multiplayer:
                        self.reset_multiplayer()
                    self._exit_callback()
                elif (
                    self._state.dead
                    and self._restart_button_rect
                    and self._restart_button_rect.collidepoint(event.pos)
                ):
                    self._controller.reload_current_level()
                    self._state = self._controller.view_state()
                elif (
                    self._state.completed
                    and self._next_button_rect
                    and self._next_button_rect.collidepoint(event.pos)
                ):
                    if self._controller.load_next_level():
                        self._state = self._controller.view_state()
        
        # Oyun state'ini güncelle - Multiplayer modunda sadece server state kullanılır
        if not self._is_multiplayer:
            # Single player: Normal state güncelleme
            self._state = self._controller.view_state()
        # Multiplayer: Server'dan gelen state zaten callback'lerde işleniyor (_on_game_state_update)
        # NOT: Multiplayer'da local hareket YAPILMAMALI - sadece server state kullanılır

    def update(self, delta: float) -> None:
        """
        Oyun güncellemesi.
        
        Multiplayer'da: Client sadece renderer - TÜM logic server'da!
        - Hasar verme → Server'da, client sadece görsel gösterir
        - Duvar kaldırma → Server'da (BREAKABLE → EMPTY), client sadece görsel günceller
        - Bomba patlama → Server'da, client sadece animasyon gösterir
        - Düşman hareketi → Server'da, client sadece pozisyonu render eder
        - Collision → Server'da, client sadece sonucu gösterir
        """
        if not self._is_multiplayer:
            # Single player: Normal update (client-side logic var)
            self._controller.update(delta)
            self._state = self._controller.view_state()
        else:
            # Multiplayer: FULL SERVER-AUTHORITATIVE
            # Client sadece renderer - hiçbir game logic yok!
            
            # Thread-safe buffer swap - en güncel bombaları al (sadece render için)
            self._server_bombs.swap_buffers()
            
            # State'i güncelle - server'dan gelen state'e göre (zaten _on_game_state_update'te güncelleniyor)
            # Burada sadece view state'i refresh et (render için)
            self._state = self._controller.view_state()
    
    def set_multiplayer(self, client, players: list[dict], level_id: str = "level_1") -> None:
        """
        Multiplayer modunu aktif et.
        
        Args:
            client: SocketIOClient instance
            players: Oyun başladığında gelen oyuncu listesi
            level_id: Level ID (server'dan gelir)
        """
        self._multiplayer_client = client
        self._is_multiplayer = True
        
        # KRİTİK: Multiplayer'da level'i yükle - _breakable_tiles set'ini doldurmak için
        logger.info(f"🎮 Loading level {level_id} for multiplayer")
        self._controller.load(level_id)
        logger.info(f"✅ Level loaded, {len(self._controller._breakable_tiles)} breakable tiles initialized")
        
        # Processed destroyed walls set'ini temizle (yeni level için)
        self._processed_destroyed_walls.clear()
        
        # Oyuncu bilgilerini kaydet
        for player in players:
            player_id = player.get("player_id")
            if player_id:
                player["position"] = self._normalize_position(player.get("position", [1, 1]))
                self._remote_players[player_id] = player
                
                # Kendi player_id'mizi bul
                if (hasattr(client, 'username') and client.username and 
                    player.get("username") == client.username):
                    self._my_player_id = player_id
                elif (hasattr(client, 'player_id') and client.player_id and 
                      player_id == client.player_id):
                    self._my_player_id = player_id
        
        # Game state callback'lerini ayarla
        if client:
            client.on_game_state(self._on_game_state_update)
            client.on_player_left(self._on_player_left)
            client.on_room_deleted(self._on_room_deleted)
    
    def reset_multiplayer(self) -> None:
        """
        Multiplayer state'ini temizle - Single player'a geçiş için.
        """
        logger.info("🔄 Resetting multiplayer state...")
        
        # Client'ı disconnect et
        if self._multiplayer_client and hasattr(self._multiplayer_client, 'disconnect'):
            try:
                self._multiplayer_client.disconnect()
                logger.info("✅ Multiplayer client disconnected")
            except Exception as e:
                logger.warning(f"⚠️ Error disconnecting client: {e}")
        
        # Multiplayer flag'ini sıfırla
        self._is_multiplayer = False
        
        # State'leri temizle
        self._multiplayer_client = None
        self._remote_players.clear()
        self._my_player_id = None
        self._server_bombs.update([])  # DoubleBufferedBombs için boş liste gönder
        self._server_enemies.clear()
        self._processed_destroyed_walls.clear()
        self._exit_reached_logged = False  # Reset exit log flag
        
        # Controller state'ini reset et (single player için hazırla)
        # NOT: Level'i reload etmeye gerek yok, single player kendi level'ini yükleyecek
        
        logger.info("✅ Multiplayer state reset complete")
    
    def _normalize_position(self, position) -> tuple[int, int]:
        """Pozisyonu tuple formatına normalize et."""
        if isinstance(position, list) and len(position) >= 2:
            return (position[0], position[1])
        elif isinstance(position, tuple) and len(position) >= 2:
            return position
        return (1, 1)  # Fallback
    
    def _on_game_state_update(self, data: dict) -> None:
        """
        Server'dan gelen game state güncellemesi.
        
        Client sadece server state'ini alır ve görsel olarak render eder.
        Hiçbir game logic yok - sadece görsel senkronizasyon!
        
        Örnekler:
        - Hasar ver → Server hasarı hesaplar, client sadece can değerini gösterir
        - Duvar kaldır → Server BREAKABLE → EMPTY yapar, client sadece görseli günceller
        - Bomba patla → Server explosion hesaplar, client sadece animasyon gösterir
        """
        # KRİTİK: Eğer multiplayer değilse, callback'i ignore et (single player'a geçiş sonrası)
        if not self._is_multiplayer:
            logger.debug("⚠️ Ignoring game state update - not in multiplayer mode")
            return
        
        # Game over kontrolü (tüm oyuncular öldü)
        game_over = data.get("game_over", False)
        if game_over:
            # Tüm oyuncular öldü - "tekrar deneyin" ekranını göster
            if self._controller.player:
                self._controller.player.health = 0  # Local player'ı ölü olarak işaretle
                self._state = self._controller.view_state()  # State'i güncelle (dead=True olacak)
                logger.info("💀 Game over: All players died")
        
        players = data.get("players", [])
        for player_data in players:
            player_id = player_data.get("player_id")
            if not player_id:
                continue
            
            pos_tuple = self._normalize_position(player_data.get("position", [0, 0]))
            player_data["position"] = pos_tuple
            
            if player_id == self._my_player_id:
                # Kendi player pozisyonumuzu server state'inden güncelle (SERVER AUTHORITATIVE)
                # CLIENT-SIDE PREDICTION YOK - Sadece server state'i uygula
                if self._controller.player:
                    old_pos = self._controller.player.position
                    old_health = self._controller.player.health
                    self._controller.player.position = pos_tuple
                    server_health = player_data.get("health", 100)
                    self._controller.player.health = server_health
                    # reached_exit bilgisini de güncelle
                    server_reached_exit = player_data.get("reached_exit", False)
                    if hasattr(self._controller.player, 'reached_exit'):
                        old_reached_exit = getattr(self._controller.player, 'reached_exit', False)
                        self._controller.player.reached_exit = server_reached_exit
                        
                        # Sadece yeni ulaşıldıysa log yaz (sürekli log yazılmasını önle)
                        if server_reached_exit and not old_reached_exit and not self._exit_reached_logged:
                            logger.info(f"🎯 Local player reached exit!")
                            self._exit_reached_logged = True
                    
                    # KRİTİK: Local player için de _remote_players'a ekle (draw metodunda kontrol için)
                    self._remote_players[player_id] = player_data
                    
                    # State'i güncelle - server'dan gelen state'e göre
                    self._state = self._controller.view_state()
                    # Debug: Position değişikliği logla
                    if old_pos != pos_tuple:
                        logger.debug(f"🔄 Local player position updated from server: {old_pos} -> {pos_tuple}")
                    if old_health != server_health:
                        logger.debug(f"❤️ Local player health updated from server: {old_health} -> {server_health}")
            else:
                # Remote player pozisyonunu güncelle
                self._remote_players[player_id] = player_data
        
        # Bombaları senkronize et (thread-safe double-buffered)
        if self._is_multiplayer:
            # Socket.IO thread'inde back buffer'a yaz
            raw_bombs = data.get("bombs", [])
            parsed_bombs = [
                {
                    "x": b.get("x", 0),
                    "y": b.get("y", 0),
                    "timer": b.get("timer", 4.0),
                    "exploded": b.get("exploded", False),
                    "explosion_timer": b.get("explosion_timer", 1.0),
                    "explosion_tiles": self._parse_explosion_tiles(b.get("explosion_tiles", []))
                }
                for b in raw_bombs
            ]
            self._server_bombs.update(parsed_bombs)
            
        # Level geçişi kontrolü
        if data.get("level_advanced", False):
            new_level_id = data.get("new_level_id", "level_1")
            logger.info(f"🎮 Level advanced to {new_level_id}")
            # Yeni level için controller'ı güncelle
            if hasattr(self._controller, 'load'):
                self._controller.load(new_level_id)
                logger.info(f"✅ Level {new_level_id} loaded on client")
            # Processed sets'leri temizle (yeni level için)
            self._processed_destroyed_walls.clear()
        
        # Düşmanları server state'inden senkronize et (Server-authoritative)
        self._server_enemies = data.get("enemies", [])
        logger.debug(f"👾 Received {len(self._server_enemies)} enemies from server")
        
        # NOT: Düşmanlara bomba hasarı artık server'da yapılıyor, client-side logic kaldırıldı
        
        # Kırılan duvarları senkronize et - her güncellemede kontrol et
        destroyed_walls = data.get("destroyed_walls", [])
        if destroyed_walls:
            logger.info(f"🧱 Received {len(destroyed_walls)} destroyed walls from server: {destroyed_walls}")
            for wall in destroyed_walls:
                wall_x = wall.get("x", 0)
                wall_y = wall.get("y", 0)
                wall_pos = (wall_x, wall_y)
                
                # KRİTİK: Bu wall zaten işlendiyse tekrar işleme (loop önleme)
                if wall_pos in self._processed_destroyed_walls:
                    logger.debug(f"⏭️ Wall at {wall_pos} already processed, skipping")
                    continue
                
                if self._controller:
                    # destroy_tile çağrısından önce kontrol et
                    if wall_pos not in self._controller._breakable_tiles:
                        logger.warning(f"⚠️ Wall at {wall_pos} not in _breakable_tiles (set has {len(self._controller._breakable_tiles)} tiles), adding it first")
                        # Eğer breakable_tiles'da yoksa, ekle (multiplayer sync için)
                        self._controller._breakable_tiles.add(wall_pos)
                    
                    # destroy_tile çağrısı - _breakable_tiles set'inden çıkarır
                    old_count = len(self._controller._breakable_tiles)
                    was_in_set = wall_pos in self._controller._breakable_tiles
                    self._controller.destroy_tile(wall_x, wall_y)
                    new_count = len(self._controller._breakable_tiles)
                    logger.info(f"🧱✅ Destroyed wall at {wall_pos} - was_in_set={was_in_set}, _breakable_tiles: {old_count} -> {new_count}")
                    
                    # Bu wall'u processed set'ine ekle (tekrar işleme önlemek için)
                    self._processed_destroyed_walls.add(wall_pos)
                    
                    # State'i güncelle - tiles() metodunun yeni state'i döndürmesi için
                    self._state = self._controller.view_state()
    
    def _parse_explosion_tiles(self, tiles: list) -> list[tuple[int, int]]:
        """Explosion tiles'ı parse et."""
        result = []
        for tile in tiles:
            if isinstance(tile, dict):
                result.append((tile.get("x", 0), tile.get("y", 0)))
            elif isinstance(tile, (list, tuple)) and len(tile) >= 2:
                result.append((tile[0], tile[1]))
        return result
    
    def _on_player_left(self, data: dict) -> None:
        """Oyuncu çıktı callback"""
        # KRİTİK: Eğer multiplayer değilse, callback'i ignore et
        if not self._is_multiplayer:
            logger.debug("⚠️ Ignoring player left event - not in multiplayer mode")
            return
        
        player_id = data.get("player_id")
        if player_id in self._remote_players:
            del self._remote_players[player_id]

    def _on_room_deleted(self, data: dict) -> None:
        """Oda silindi callback - menüye dön"""
        # KRİTİK: Eğer multiplayer değilse, callback'i ignore et
        if not self._is_multiplayer:
            logger.debug("⚠️ Ignoring room deleted event - not in multiplayer mode")
            return
        
        message = data.get("message", "Oda silindi")
        logger.info(f"💀 Room deleted: {message}")
        
        # Multiplayer state'ini temizle
        self.reset_multiplayer()
        
        # Menüye dön (exit_callback kullan)
        if self._exit_callback:
            # Thread-safe: Pygame event gönder (callback main thread'de çalışsın)
            import pygame
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"action": "room_deleted"}))
            # Direkt callback çağrısı (hemen menüye dön)
            self._exit_callback()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill((5, 6, 15))
        renderer_width = self._controller.current_level().width * self._renderer.tile_size
        renderer_height = self._controller.current_level().height * self._renderer.tile_size
        offset_x = (surface.get_width() - renderer_width) // 2
        offset_y = (surface.get_height() - renderer_height) // 2
        self._draw_level_header(surface)
        self._renderer.draw(
            surface,
            self._controller.tiles(),
            offset=(offset_x, offset_y),
            theme=self._controller.current_theme(),
        )
        player = self._controller.player
        tile_size = self._renderer.tile_size
        
        # Remote player'ları çiz (multiplayer modunda)
        if self._is_multiplayer:
            for player_id, player_data in self._remote_players.items():
                # Ölü oyuncuları çizme
                if player_data.get("health", 0) <= 0:
                    continue
                
                # Exit'e ulaşan oyuncuları çizme
                if player_data.get("reached_exit", False):
                    continue
                
                # Kendi oyuncumuzu çizme (zaten local player olarak çiziliyor)
                if player_id == self._my_player_id:
                    continue
                
                pos_tuple = self._normalize_position(player_data.get("position", (0, 0)))
                
                remote_rect = pygame.Rect(
                    offset_x + pos_tuple[0] * tile_size,
                    offset_y + pos_tuple[1] * tile_size,
                    tile_size,
                    tile_size,
                )
                # Remote player için farklı renk/sprite kullan (veya aynı sprite)
                if self._player_sprite:
                    # Remote player'ı biraz farklı göster (örneğin daha soluk)
                    temp_surface = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                    self._player_sprite.draw(temp_surface, pygame.Rect(0, 0, tile_size, tile_size))
                    temp_surface.set_alpha(180)  # Biraz şeffaf
                    surface.blit(temp_surface, remote_rect)
                
                # Remote player username göster
                username = player_data.get("username", "Player")
                font = pygame.font.Font(None, 20)
                username_text = font.render(username, True, (200, 200, 200))
                username_rect = username_text.get_rect(center=(remote_rect.centerx, remote_rect.top - 10))
                surface.blit(username_text, username_rect)
        
        # Local player'ı çiz (sadece canlıysa ve exit'e ulaşmamışsa)
        if player and self._player_sprite and player.health > 0:
            # Exit'e ulaşan oyuncuları çizme (multiplayer'da server state'inden kontrol et)
            reached_exit = False
            if self._is_multiplayer:
                my_player_data = self._remote_players.get(self._my_player_id, {})
                reached_exit = my_player_data.get("reached_exit", False)
            else:
                # Single player: controller'dan kontrol et
                reached_exit = getattr(player, 'reached_exit', False)
            
            if not reached_exit:
                rect = pygame.Rect(
                    offset_x + player.position[0] * tile_size,
                    offset_y + player.position[1] * tile_size,
                    tile_size,
                    tile_size,
                )
                self._player_sprite.draw(surface, rect)
        # Bombaları çiz - Thread-safe: Front buffer'dan bombaları al (swap edilmiş, güncel)
        bombs_to_draw = self._server_bombs.get_bombs() if self._is_multiplayer else self._state.bombs
        
        for bomb in bombs_to_draw:
            # Bomb verilerini al
            if isinstance(bomb, dict):
                bomb_x, bomb_y = bomb.get("x", 0), bomb.get("y", 0)
                bomb_exploded = bomb.get("exploded", False)
                explosion_timer = bomb.get("explosion_timer", 1.0)
                explosion_tiles = bomb.get("explosion_tiles", [])
            else:
                bomb_x, bomb_y = bomb.x, bomb.y
                bomb_exploded = bomb.exploded
                explosion_timer = getattr(bomb, "explosion_timer", 1.0)
                explosion_tiles = getattr(bomb, "explosion_tiles", [])
            
            bomb_rect = pygame.Rect(
                offset_x + bomb_x * tile_size,
                offset_y + bomb_y * tile_size,
                tile_size,
                tile_size,
            )
            
            if not bomb_exploded and self._bomb_image:
                # Normal bomba
                scaled = pygame.transform.smoothscale(self._bomb_image, (tile_size, tile_size))
                surface.blit(scaled, bomb_rect)
            elif bomb_exploded and explosion_timer > 0 and self._explosion_image:
                # Patlama animasyonu
                scaled = pygame.transform.smoothscale(self._explosion_image, (tile_size, tile_size))
                if explosion_tiles:
                    # Explosion tiles'ı kullan
                    for tx, ty in explosion_tiles:
                        explosion_rect = pygame.Rect(
                            offset_x + tx * tile_size,
                            offset_y + ty * tile_size,
                            tile_size,
                            tile_size,
                        )
                        surface.blit(scaled, explosion_rect)
                else:
                    # Fallback: Merkez patlama
                    surface.blit(scaled, bomb_rect)
        
        # Power-up'ları çiz
        for powerup in self._state.powerups:
            powerup_rect = pygame.Rect(
                offset_x + powerup.x * tile_size,
                offset_y + powerup.y * tile_size,
                tile_size,
                tile_size,
            )
            # Power-up tipine göre renk/şekil çiz (basit implementasyon)
            powerup_color = {
                "speed": (255, 255, 0),  # Sarı
                "bomb_count": (0, 255, 0),  # Yeşil
                "bomb_power": (255, 0, 0),  # Kırmızı
                "health": (0, 0, 255),  # Mavi
            }.get(powerup.powerup_type, (255, 255, 255))
            pygame.draw.circle(surface, powerup_color, powerup_rect.center, tile_size // 3)
            pygame.draw.circle(surface, (255, 255, 255), powerup_rect.center, tile_size // 3, 2)
        
        self._draw_enemies(surface, offset_x, offset_y)
        self._draw_exit_button(surface)
        self._draw_health(surface)
        self._draw_bomb_count(surface)
        if self._state.completed:
            self._draw_completion_ui(surface)
        else:
            self._next_button_rect = None
        if self._state.dead:
            self._draw_death_overlay(surface)
            self._draw_death_ui(surface)
        else:
            self._restart_button_rect = None

    def _draw_health(self, surface: pygame.Surface) -> None:
        player = self._state.player
        if player.position is None:
            return
        font = pygame.font.Font(None, 22)
        text = font.render(f"Can: {player.health}", True, (255, 160, 160))
        padding = 14
        rect = text.get_rect(topleft=(padding, padding))
        background = pygame.Rect(rect.left - 6, rect.top - 4, rect.width + 12, rect.height + 8)
        pygame.draw.rect(surface, (20, 20, 20), background, border_radius=6)
        pygame.draw.rect(surface, (255, 255, 255), background, 1, border_radius=6)
        surface.blit(text, rect)
    
    def _draw_bomb_count(self, surface: pygame.Surface) -> None:
        """Bomba sayısı UI'ı çiz - aktif/maksimum bomba sayısını göster"""
        if not self._controller.player:
            return
        
        # Aktif bomba sayısını hesapla - Thread-safe: Aktif bombaları al
        if self._is_multiplayer:
            active_bombs = len(self._server_bombs.get_active_bombs())
        else:
            active_bombs = sum(1 for b in self._state.bombs if not b.exploded)
        
        # Font ve text - sadece aktif bomba sayısı (limit yok)
        font = pygame.font.Font(None, 22)
        bomb_text = f"Bombalar: {active_bombs}"
        
        # Her zaman yeşil renk (limit kontrolü yok)
        text_color = (160, 255, 160)
        text = font.render(bomb_text, True, text_color)
        
        # Health'in altına yerleştir
        padding = 14
        health_height = 30  # Health text'in yüksekliği
        rect = text.get_rect(topleft=(padding, padding + health_height))
        
        # Background
        background = pygame.Rect(rect.left - 6, rect.top - 4, rect.width + 12, rect.height + 8)
        pygame.draw.rect(surface, (20, 20, 20), background, border_radius=6)
        pygame.draw.rect(surface, (255, 255, 255), background, 1, border_radius=6)
        
        surface.blit(text, rect)

    def _draw_enemies(self, surface: pygame.Surface, offset_x: int, offset_y: int) -> None:
        tile_size = self._renderer.tile_size
        
        # Multiplayer: Server'dan gelen düşmanları render et
        if self._is_multiplayer:
            for enemy_data in self._server_enemies:
                if not enemy_data.get("alive", True):
                    continue
                
                # Enemy type'ı string'den EnemyType enum'una çevir
                enemy_type_str = enemy_data.get("enemy_type", "chasing").upper()
                try:
                    enemy_type = EnemyType[enemy_type_str]
                except KeyError:
                    enemy_type = EnemyType.CHASING  # Fallback
                
                image = self._enemy_images.get(enemy_type)
                if image:
                    pos = enemy_data.get("position", [0, 0])
                    if isinstance(pos, list) and len(pos) >= 2:
                        enemy_x, enemy_y = pos[0], pos[1]
                    elif isinstance(pos, tuple) and len(pos) >= 2:
                        enemy_x, enemy_y = pos[0], pos[1]
                    else:
                        continue
                    
                    rect = pygame.Rect(
                        offset_x + enemy_x * tile_size,
                        offset_y + enemy_y * tile_size,
                        tile_size,
                        tile_size,
                    )
                    scaled = pygame.transform.smoothscale(image, (tile_size, tile_size))
                    surface.blit(scaled, rect)
                    # Health göster (server'dan gelen health)
                    health = enemy_data.get("health", 100)
                    if health < 100:
                        font = pygame.font.Font(None, 16)
                        health_text = font.render(f"{health}", True, (255, 100, 100))
                        health_rect = health_text.get_rect(center=(rect.centerx, rect.top - 8))
                        surface.blit(health_text, health_rect)
        else:
            # Single player: Client-side enemies
            for enemy in self._state.enemies:
                if not enemy.alive:
                    continue
                image = self._enemy_images.get(enemy.enemy_type)
                if image:
                    rect = pygame.Rect(
                        offset_x + enemy.position[0] * tile_size,
                        offset_y + enemy.position[1] * tile_size,
                        tile_size,
                        tile_size,
                    )
                    scaled = pygame.transform.smoothscale(image, (tile_size, tile_size))
                    surface.blit(scaled, rect)
                    self._draw_enemy_health(surface, enemy, rect)

    def _draw_enemy_health(self, surface: pygame.Surface, enemy, enemy_rect: pygame.Rect) -> None:
        """Canavarın can çubuğunu çizer"""
        if enemy.health >= enemy.max_health:
            return
        
        bar_width = enemy_rect.width - 4
        bar_height = 4
        bar_x = enemy_rect.x + 2
        bar_y = enemy_rect.y + 2
        
        # Arka plan (kırmızı)
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(surface, (150, 0, 0), bg_rect)
        
        # Can çubuğu (yeşil)
        health_percentage = 0.0 if enemy.max_health == 0 else max(0.0, min(1.0, enemy.health / enemy.max_health))
        health_width = int(bar_width * health_percentage)
        if health_width > 0:
            health_rect = pygame.Rect(bar_x, bar_y, health_width, bar_height)
            # Can yüzdesine göre renk (yeşil -> sarı -> kırmızı)
            if health_percentage > 0.5:
                color = (0, 200, 0)  # Yeşil
            elif health_percentage > 0.25:
                color = (200, 200, 0)  # Sarı
            else:
                color = (200, 100, 0)  # Turuncu
            pygame.draw.rect(surface, color, health_rect)
        
        # Çerçeve
        pygame.draw.rect(surface, (255, 255, 255), bg_rect, 1)

    def _draw_death_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), flags=pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

    def _draw_completion_ui(self, surface: pygame.Surface) -> None:
        title_font = pygame.font.Font(None, 34)
        title_text = title_font.render("Level Tamamlandı!", True, (255, 220, 100))
        surface.blit(title_text, title_text.get_rect(center=(surface.get_width() // 2, 40)))
        button_font = pygame.font.Font(None, 26)
        button_text = button_font.render("Sonraki Seviye", True, (20, 20, 20))
        button_rect = pygame.Rect(0, 0, 200, 46)
        button_rect.center = (surface.get_width() // 2, 100)
        pygame.draw.rect(surface, (255, 205, 58), button_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), button_rect, 2, border_radius=8)
        surface.blit(button_text, button_text.get_rect(center=button_rect.center))
        self._next_button_rect = button_rect

    def _draw_level_header(self, surface: pygame.Surface) -> None:
        index = self._controller.current_level_index()
        total = self._controller.level_count()
        if index is None or total == 0:
            return
        font = pygame.font.Font(None, 28)
        header = font.render(f"Seviye {index}/{total}", True, (255, 235, 160))
        surface.blit(header, header.get_rect(center=(surface.get_width() // 2, 20)))

    def _draw_exit_button(self, surface: pygame.Surface) -> None:
        button_width = 140
        button_height = 42
        margin = 16
        rect = pygame.Rect(
            surface.get_width() - button_width - margin,
            margin,
            button_width,
            button_height,
        )
        pygame.draw.rect(surface, (220, 60, 60), rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), rect, 2, border_radius=8)
        font = pygame.font.Font(None, 24)
        text = font.render("Ana Menü", True, (255, 255, 255))
        surface.blit(text, text.get_rect(center=rect.center))
        self._exit_button_rect = rect

    def _play_primed_sound(self) -> None:
        self._sound_service.play_sound("patlama.wav")

    def _draw_death_ui(self, surface: pygame.Surface) -> None:
        title_font = pygame.font.Font(None, 34)
        title_text = title_font.render("Yeniden dene!", True, (255, 120, 120))
        surface.blit(title_text, title_text.get_rect(center=(surface.get_width() // 2, 40)))
        button_font = pygame.font.Font(None, 26)
        button_text = button_font.render("Yeniden Dene", True, (20, 20, 20))
        button_rect = pygame.Rect(0, 0, 220, 46)
        button_rect.center = (surface.get_width() // 2, 110)
        pygame.draw.rect(surface, (255, 120, 120), button_rect, border_radius=8)
        pygame.draw.rect(surface, (255, 255, 255), button_rect, 2, border_radius=8)
        surface.blit(button_text, button_text.get_rect(center=button_rect.center))
        self._restart_button_rect = button_rect

