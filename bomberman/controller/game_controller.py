"""
Game controller: oyun akışının tamamını yönetir (hareket, bomba, hasar, seviye ilerleme).
View sadece intent iletir ve state okur.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Optional

from model.bomberman import Bomberman

logger = logging.getLogger(__name__)
from model.enemy import ChasingEnemy, Enemy, EnemyType, SmartEnemy, StaticEnemy
from model.level import LevelConfig, TileType, Theme
from service.collision_service import CollisionService
from service.explosion_service import ExplosionService
from service.game_event_service import GameEventService, GameEventType
from service.game_observers import LoggerObserver, ScoreObserver, SoundObserver
from service.level_service import LevelService
from service.powerup_service import PowerupService
from service.sound_service import SoundService
from service.user_progress_service import UserProgressService
from view.characters import CharacterFactory
from model.player_decorator import BombermanAdapter, PlayerInterface


class GameController:
    def __init__(
        self,
        level_service: Optional[LevelService] = None,
        collision_service: Optional[CollisionService] = None,
        explosion_service: Optional[ExplosionService] = None,
        powerup_service: Optional[PowerupService] = None,
        sound_service: Optional[SoundService] = None,
        progress_service: Optional[UserProgressService] = None,
        event_service: Optional[GameEventService] = None,
    ) -> None:
        self._level_service = level_service or LevelService()
        self._collision_service = collision_service or CollisionService()
        self._explosion_service = explosion_service or ExplosionService()
        self._powerup_service = powerup_service or PowerupService()
        self._sound_service = sound_service  # Optional
        self._progress_service = progress_service  # Optional
        self._event_service = event_service or GameEventService()
        self._current_user_id = None  # AuthService'den set edilecek
        
        # Observerları ekle
        if sound_service:
            self._event_service.attach(SoundObserver(sound_service))
        self._score_observer = ScoreObserver()
        self._event_service.attach(self._score_observer)
        self._event_service.attach(LoggerObserver())
        self._current: Optional[LevelConfig] = None
        self._current_id: Optional[str] = None
        self._breakable_tiles: set[tuple[int, int]] = set()
        self._hard_tiles: dict[tuple[int, int], int] = {}
        self.player: Bomberman | None = None
        self._enemies: list[Enemy] = []
        self._enemy_timers: dict[int, float] = {}
        self._blocked_positions: set[tuple[int, int]] = set()
        self._theme_override: Theme | None = None
        self._bombs: list["GameController.Bomb"] = []
        self._dead: bool = False
        self._completed: bool = False
        self._last_collision_enemy: Enemy | None = None
        self._player_decorator: Optional[PlayerInterface] = None  # Decorator Pattern: Power-up decorator chain
        self._enemy_last_positions: dict[int, tuple[int, int]] = {}  # Düşman ID → son pozisyon

    @dataclass
    class Bomb:
        x: int
        y: int
        timer: float = 4.0
        explosion_timer: float = 0.5
        exploded: bool = False
        explosion_tiles: list[tuple[int, int]] = field(default_factory=list)
        damage_applied: bool = False

    @dataclass(frozen=True)
    class BombView:
        x: int
        y: int
        exploded: bool
        explosion_tiles: tuple[tuple[int, int], ...]

    @dataclass(frozen=True)
    class EnemyView:
        position: tuple[int, int]
        enemy_type: EnemyType
        health: int
        max_health: int
        alive: bool

    @dataclass(frozen=True)
    class PlayerView:
        position: tuple[int, int] | None
        health: int
        alive: bool

    @dataclass(frozen=True)
    class PowerupView:
        x: int
        y: int
        powerup_type: str

    @dataclass(frozen=True)
    class GameViewState:
        player: "GameController.PlayerView"
        bombs: tuple["GameController.BombView", ...]
        enemies: tuple["GameController.EnemyView", ...]
        powerups: tuple["GameController.PowerupView", ...]
        completed: bool
        dead: bool

    def load(self, level_id: str) -> LevelConfig:
        # LevelService kullanarak level yükle
        level = self._level_service.load_level(level_id)
        self._current = level
        self._current_id = level_id
        self._breakable_tiles = {
            (tile.x, tile.y)
            for tile in level.tiles
            if tile.type == TileType.BREAKABLE
        }
        self._hard_tiles = {
            (tile.x, tile.y): 2
            for tile in level.tiles
            if tile.type == TileType.HARD
        }
        self._bombs = []
        roster = CharacterFactory.roster()
        character = roster[0] if roster else None
        if character:
            self.player = Bomberman(character=character, position=level.player_start)
        self._spawn_enemies(level)
        self._dead = False
        self._completed = False
        self._collision_service.reset()
        self._last_collision_enemy = None
        self._player_decorator = None  # Decorator Pattern: Yeni level'da decorator'ı sıfırla
        return level

    def set_blocked_positions(self, positions: Iterable[tuple[int, int]]) -> None:
        self._blocked_positions = set(positions)

    def enemies(self) -> tuple[Enemy, ...]:
        return tuple(self._enemies)
    
    def _instantiate_enemy(self, enemy_type: EnemyType, position: tuple[int, int]) -> Enemy | None:
        # Factory Method Pattern: MonsterFactory kullanarak düşman oluştur
        from view.characters import MonsterFactory
        return MonsterFactory.create(enemy_type, position)

    def _spawn_enemies(self, level: LevelConfig) -> None:
        self._enemies = []
        positions = iter(level.enemy_positions)
        self._enemy_timers.clear()
        for spawn in level.enemy_spawns:
            enemy_type = EnemyType[spawn["type"]]
            for _ in range(spawn["count"]):
                try:
                    pos = next(positions)
                except StopIteration:
                    break
                enemy = self._instantiate_enemy(enemy_type, pos)
                if enemy:
                    self._enemies.append(enemy)
                    self._enemy_timers[id(enemy)] = 0.0

    
        

    def update_enemies(self, delta: float) -> None:
        player_pos = self.player.position if self.player else None
        for enemy in self._enemies:
            if not enemy.is_alive():
                continue
            
            # Enemy update'inden ÖNCE pozisyonu kaydet
            enemy_id = id(enemy)
            if enemy_id not in self._enemy_last_positions:
                self._enemy_last_positions[enemy_id] = enemy.position
            
            timer = self._enemy_timers.get(enemy_id, 0.0) + delta
            interval = enemy.movement_interval()
            if timer >= interval:
                # Hareket öncesi pozisyonu kaydet
                self._enemy_last_positions[enemy_id] = enemy.position
                # Şimdi hareket ettir
                enemy.update(player_pos, self.enemy_tile_type_at)
                timer -= interval
            self._enemy_timers[enemy_id] = timer

    def enemy_tile_type_at(self, x: int, y: int) -> TileType:
        """Düşmanlar için tile tipini döndürür - harita sınırları ve duvarlar kontrol edilir"""
        level = self.current_level()
        
        # Harita sınırları kontrolü
        if x < 0 or x >= level.width or y < 0 or y >= level.height:
            return TileType.UNBREAKABLE
        
        base = level.tile_at(x, y)
        
        # Engellenmiş pozisyonlar (bomba, oyuncu, diğer düşmanlar)
        # Düşmanlar oyuncunun pozisyonuna geçemez
        if (x, y) in self._blocked_positions:
            return TileType.UNBREAKABLE
        
        # Düşmanlar kırılabilir duvarların içinden geçemez
        if base == TileType.BREAKABLE:
            return TileType.BREAKABLE  # Geçilemez
        
        # Hard duvarlar da geçilemez
        if base == TileType.HARD:
            return TileType.HARD  # Geçilemez
        
        # Sadece EMPTY ve EXIT geçilebilir
        return base

    def current_level_id(self) -> Optional[str]:
        return self._current_id

    def reload_current_level(self) -> None:
        if self._current_id is None:
            return
        self.load(self._current_id)

    def set_theme_override(self, theme: Theme) -> None:
        self._theme_override = theme

    def current_theme(self) -> Theme:
        if self._theme_override is not None:
            return self._theme_override
        return self.current_level().theme

    def load_theme_level(self, theme: Theme) -> bool:
        # Tüm level'leri kontrol et ve tema eşleşen ilkini yükle
        for level_id in self._level_service.list_all_levels():
            level = self.load(level_id)
            if level.theme == theme:
                return True
        return False

    def load_next_level(self) -> bool:
        success = self._level_service.load_next_level() and (
            self.load(self._level_service.get_current_level_id() or "") is not None
        )
        
        # Başarılı level geçişinde progress'i kaydet
        if success and self._progress_service and self._current_user_id:
            next_level_id = self._level_service.get_current_level_id()
            if next_level_id:
                self._progress_service.save_progress(self._current_user_id, next_level_id)
        
        return success

    def current_level_index(self) -> Optional[int]:
        return self._level_service.get_current_level_index()

    def level_count(self) -> int:
        return self._level_service.get_level_count()

    def current_level(self) -> LevelConfig:
        if self._current is None:
            raise RuntimeError("Level yüklenmedi.")
        return self._current
    
    def set_current_user_id(self, user_id) -> None:
        """AuthService'den giriş yapan kullanıcı ID'sini set et."""
        self._current_user_id = user_id

    def destroy_tile(self, x: int, y: int) -> None:
        """Kırılabilir duvarı yok et - _breakable_tiles set'inden çıkar"""
        was_in_set = (x, y) in self._breakable_tiles
        if was_in_set:
            self._breakable_tiles.remove((x, y))
            # Observer Pattern: Duvar yıkıldı event'i
            self._event_service.emit(
                GameEventType.WALL_DESTROYED,
                position=(x, y),
                wall_type="breakable"
            )
        else:
            # Eğer set'te yoksa, muhtemelen zaten yok edilmiş veya hiç olmamış
            # Multiplayer'da bu normal olabilir (server'dan gelen destroyed_walls)
            # Power-up spawn kontrolü devre dışı - kullanıcı istemiyor
            pass

    def tiles(self) -> Iterable[tuple[int, int, TileType]]:
        level = self.current_level()
        for tile in level.tiles:
            if tile.type == TileType.BREAKABLE and (tile.x, tile.y) not in self._breakable_tiles:
                yield tile.x, tile.y, TileType.EMPTY
            elif tile.type == TileType.HARD and (tile.x, tile.y) not in self._hard_tiles:
                yield tile.x, tile.y, TileType.EMPTY
            else:
                yield tile.x, tile.y, tile.type

    def tile_type_at(self, x: int, y: int) -> TileType:
        level = self.current_level()
        if x < 0 or y < 0 or x >= level.width or y >= level.height:
            return TileType.UNBREAKABLE
        base = level.tile_at(x, y)
        if base == TileType.BREAKABLE and (x, y) not in self._breakable_tiles:
            return TileType.EMPTY
        if base == TileType.HARD and (x, y) not in self._hard_tiles:
            return TileType.EMPTY
        return base

    def is_exit(self, x: int, y: int) -> bool:
        return self.tile_type_at(x, y) == TileType.EXIT

    def reached_exit(self, x: int, y: int) -> bool:
        if self.player:
            return self.player.position == (x, y) and self.is_exit(x, y)
        return False

    def move_player(self, dx: int, dy: int) -> None:
        if self.player is None:
            return
        if self._dead:
            return
        width = self.current_level().width
        height = self.current_level().height
        new_x = max(0, min(width - 1, self.player.position[0] + dx))
        new_y = max(0, min(height - 1, self.player.position[1] + dy))
        if self._is_blocked(new_x, new_y):
            return
        tile = self.tile_type_at(new_x, new_y)
        if tile == TileType.EMPTY or tile == TileType.EXIT:
            self.player.position = (new_x, new_y)

    def place_bomb(self) -> None:
        """Oyuncunun mevcut pozisyonuna bomba bırakır."""
        player = self.player
        if player is None or self._dead:
            return
        pos = player.position
        if any((b.x, b.y) == pos and not b.exploded for b in self._bombs):
            return
        active_bombs = sum(1 for b in self._bombs if not b.exploded)
        if active_bombs >= player.bomb_count:
            return
        self._bombs.append(self.Bomb(pos[0], pos[1]))

    def update(self, delta: float) -> None:
        """Oyun içi state güncellemesi (bombalar, düşmanlar, çarpışmalar)."""
        if self.player is None or self._current is None:
            return
        if self._dead:
            self._bombs.clear()
            return

        self._update_bombs(delta)
        self._update_blocked_positions()
        self.update_enemies(delta)
        self._check_player_enemy_collision(delta)
        # Power-up sistemi aktif
        self._check_powerup_collection()  # Decorator Pattern: Power-up toplama kontrolü
        self._completed = self.is_exit(*self.player.position)
    
    def _check_powerup_collection(self) -> None:
        """
        Power-up toplama kontrolü - Decorator Pattern kullanır.
        Oyuncu power-up üzerindeyse, decorator chain'e ekler ve Bomberman'a uygular.
        """
        if self.player is None:
            return
        
        # Power-up'ları kontrol et
        collected_powerups = self._powerup_service.check_collection(self.player.position)
        
        # Toplanan her power-up için decorator uygula
        for powerup_type in collected_powerups:
            # Decorator Pattern: Power-up'ı decorator chain'e ekle
            if self._player_decorator is None:
                # İlk power-up: Bomberman'ı adapter ile wrap et
                self._player_decorator = BombermanAdapter(self.player)
            
            # Decorator Pattern: Yeni decorator ekle
            self._player_decorator = self._powerup_service.apply_powerup(
                powerup_type, 
                self._player_decorator
            )
            
            # Decorator'dan değerleri al ve Bomberman'a uygula 
           
            self.player.speed = self._player_decorator.get_speed()
            self.player.bomb_count = self._player_decorator.get_bomb_count()
            self.player.bomb_power = self._player_decorator.get_bomb_power()
            if powerup_type.value == "health":
                self.player.health = self._player_decorator.get_health()
            
            # Observer Pattern: Power-up toplandı event'i
            self._event_service.emit(
                GameEventType.POWERUP_COLLECTED,
                position=self.player.position,
                powerup_type=powerup_type.value
            )

    def view_state(self) -> "GameController.GameViewState":
        player_view = self.PlayerView(
            position=self.player.position if self.player else None,
            health=self.player.health if self.player else 0,
            alive=self.player.is_alive() if self.player else False,
        )
        bombs = tuple(
            self.BombView(
                x=b.x,
                y=b.y,
                exploded=b.exploded,
                explosion_tiles=tuple(b.explosion_tiles),
            )
            for b in self._bombs
        )
        enemies = tuple(
            self.EnemyView(
                position=e.position,
                enemy_type=e.enemy_type,
                health=e.health,
                max_health=e.max_health,
                alive=e.is_alive(),
            )
            for e in self._enemies
        )
        # Power-up sistemi devre dışı - kullanıcı istemiyor
        # powerups = tuple(
        #     self.PowerupView(
        #         x=p.x,
        #         y=p.y,
        #         powerup_type=p.type.value
        #     )
        #     for p in self._powerup_service.get_active_powerups()
        # )
        powerups = tuple()  # Boş tuple - power-up yok
        return self.GameViewState(
            player=player_view,
            bombs=bombs,
            enemies=enemies,
            powerups=powerups,
            completed=self._completed,
            dead=self._dead,
        )

    def is_dead(self) -> bool:
        return self._dead

    def explode_at(self, x: int, y: int, radius: int = 1) -> list[tuple[int, int]]:
        if self._hard_tiles.get((x, y)):
            return []
        
        # ExplosionService ile patlama tile'larını hesapla
        def is_blocked(tx: int, ty: int) -> bool:
            return self.tile_type_at(tx, ty) == TileType.UNBREAKABLE
        
        affected = self._explosion_service.calculate_explosion_tiles(x, y, radius, is_blocked)
        
        # Tile'ları destroy et
        for tx, ty in affected:
            if (tx, ty) == (x, y):
                self.destroy_tile(x, y)
            else:
                tile_type = self.tile_type_at(tx, ty)
                if tile_type == TileType.HARD:
                    self._hard_tiles[(tx, ty)] = self._hard_tiles.get((tx, ty), 2) - 1
                    if self._hard_tiles[(tx, ty)] <= 0:
                        del self._hard_tiles[(tx, ty)]
                        # Observer Pattern: Hard duvar yıkıldı
                        self._event_service.emit(
                            GameEventType.WALL_DESTROYED,
                            position=(tx, ty),
                            wall_type="hard"
                        )
                else:
                    self.destroy_tile(tx, ty)
        
        return affected

    def _update_bombs(self, delta: float) -> None:
        for bomb in self._bombs:
            bomb.timer -= delta
            if bomb.timer <= 0 and not bomb.exploded:
                bomb.exploded = True
                player = self.player
                bomb_power = player.bomb_power if player else 1
                bomb.explosion_tiles = self.explode_at(bomb.x, bomb.y, radius=bomb_power)
                
                # Observer Pattern: Bomba patladı event'i
                self._event_service.emit(
                    GameEventType.BOMB_EXPLODED,
                    position=(bomb.x, bomb.y),
                    radius=bomb_power,
                    affected_tiles=bomb.explosion_tiles
                )
                
            if bomb.exploded:
                if not bomb.damage_applied:
                    self._apply_explosion_damage(bomb.explosion_tiles)
                    bomb.damage_applied = True
                bomb.explosion_timer -= delta
        self._bombs = [b for b in self._bombs if not (b.exploded and b.explosion_timer <= 0)]

    def _update_blocked_positions(self) -> None:
        """Engellenmiş pozisyonları güncelle - bombalar, oyuncular, düşmanlar"""
        blockers: set[tuple[int, int]] = set()
        # Bombalar (patlamamış olanlar)
        blockers.update((b.x, b.y) for b in self._bombs if not b.exploded)
        # Oyuncu
        if self.player:
            blockers.add(self.player.position)
        # Düşmanlar
        blockers.update(enemy.position for enemy in self._enemies if enemy.is_alive())
        self.set_blocked_positions(blockers)

    def _check_player_enemy_collision(self, delta: float) -> None:
        if self._dead:
            return
        player = self.player
        if not player:
            return

        player_pos = player.position
        collision_detected = False
        current_collision_enemy: Enemy | None = None

        # Çarpışma algılama
        for enemy in self._enemies:
            if not enemy.is_alive():
                continue
            
            # Düşman hareket ediyor mu kontrol et (pozisyon update_enemies'de kaydedildi)
            enemy_id = id(enemy)
            last_pos = self._enemy_last_positions.get(enemy_id)
            enemy_is_moving = last_pos != enemy.position if last_pos else True
            
            if self._collision_service.check_proximity(player_pos, enemy.position, enemy_is_moving):
                collision_detected = True
                current_collision_enemy = enemy
                break

        # Çarpışma durumunu güncelle
        same_enemy = current_collision_enemy == self._last_collision_enemy
        self._collision_service.update_collision(delta, collision_detected, same_enemy)
        self._last_collision_enemy = current_collision_enemy

        if collision_detected:
            # Hasar uygulanmalı mı kontrol et
            if self._collision_service.should_apply_damage():
                player.take_damage(10)
                self._collision_service.reset_damage_cooldown()
                
                # Düşman saldırı sesi çal
                if self._sound_service:
                    self._sound_service.play_sound("enemy_attack.wav")

            if not player.is_alive():
                self._dead = True
                self._bombs.clear()
    
    def _check_player_enemy_collision_multiplayer(self, delta: float, multiplayer_client) -> None:
        """
        Multiplayer modunda düşman-oyuncu collision kontrolü.
        Hasar server'a bildirilir, client-side'da direkt uygulanmaz.
        """
        if self._dead:
            return
        player = self.player
        if not player:
            return

        player_pos = player.position
        collision_detected = False
        current_collision_enemy: Enemy | None = None

        # Çarpışma algılama
        for enemy in self._enemies:
            if not enemy.is_alive():
                continue
            
            # Düşman hareket ediyor mu kontrol et
            enemy_id = id(enemy)
            last_pos = self._enemy_last_positions.get(enemy_id)
            enemy_is_moving = last_pos != enemy.position if last_pos else True
            
            if self._collision_service.check_proximity(player_pos, enemy.position, enemy_is_moving):
                collision_detected = True
                current_collision_enemy = enemy
                break

        # Çarpışma durumunu güncelle
        same_enemy = current_collision_enemy == self._last_collision_enemy
        self._collision_service.update_collision(delta, collision_detected, same_enemy)
        self._last_collision_enemy = current_collision_enemy

        if collision_detected:
            # Hasar uygulanmalı mı kontrol et
            if self._collision_service.should_apply_damage():
                # Multiplayer: Hasarı server'a bildir (client-side'da direkt uygulama)
                if multiplayer_client and hasattr(multiplayer_client, 'send_player_damage'):
                    multiplayer_client.send_player_damage(10)
                else:
                    # Fallback: Eğer client yoksa local uygula
                    player.take_damage(10)
                
                self._collision_service.reset_damage_cooldown()
                
                # Düşman saldırı sesi çal
                if self._sound_service:
                    self._sound_service.play_sound("enemy_attack.wav")

    def _apply_explosion_damage_to_enemies(self, tiles: list[tuple[int, int]]) -> None:
        """Multiplayer'da server'dan gelen explosion tiles'ı kullanarak düşmanlara hasar ver"""
        if not tiles:
            return
        
        damage = self.current_level().explosion_damage
        
        # Düşmanlara hasar ver
        for enemy in self._enemies:
            if enemy.is_alive() and enemy.position in tiles:
                old_health = enemy.health
                enemy.take_damage(damage)
                logger.info(f"💥 Enemy at {enemy.position} took {damage} damage from explosion: {old_health} -> {enemy.health} HP")
                if not enemy.is_alive():
                    # Observer Pattern: Düşman öldü event'i
                    self._event_service.emit(
                        GameEventType.ENEMY_KILLED,
                        enemy_type=enemy.enemy_type.value,
                        position=enemy.position
                    )

    def _apply_explosion_damage(self, tiles: list[tuple[int, int]]) -> None:
        player = self.player
        damage = self.current_level().explosion_damage
        
        if player:
            # ExplosionService ile hasar uygula
            player_died = self._explosion_service.apply_damage_to_targets(
                tiles,
                player.position,
                player.take_damage,
                player.is_alive,
                self._enemies,
                damage,
            )
            if player_died:
                self._dead = True
                self._bombs.clear()
                # Observer Pattern: Oyuncu öldü event'i
                self._event_service.emit(GameEventType.PLAYER_DIED, position=player.position)
            
            # Ölen düşmanları kontrol et ve event yayınla
            for enemy in self._enemies:
                if not enemy.is_alive() and enemy.position in tiles:
                    # Observer Pattern: Düşman öldü event'i
                    self._event_service.emit(
                        GameEventType.ENEMY_KILLED,
                        enemy_type=enemy.enemy_type.value,
                        position=enemy.position
                    )
        else:
            # Oyuncu yok ise sadece düşmanlara hasar
            self._explosion_service.apply_damage_to_targets(
                tiles,
                (-1, -1),  # Geçersiz pozisyon
                lambda x: None,  # No-op
                lambda: False,
                self._enemies,
                damage,
            )

    def _is_blocked(self, x: int, y: int) -> bool:
        if any((b.x, b.y) == (x, y) and not b.exploded for b in self._bombs):
            return True
        if any(enemy.position == (x, y) and enemy.is_alive() for enemy in self._enemies):
            return True
        return False

