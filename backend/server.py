"""
Bomberman Multiplayer Server - Socket.io
Port 7777'de çalışır, oyuncuların oda kurması ve beraber oyun oynamasını sağlar.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio
from aiohttp import web

from config.database import POSTGRESQL_CONNECTION_STRING
from handlers.game_handlers import GameHandlers
from handlers.room_handlers import RoomHandlers
from models.room import GameRoom

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Socket.io server oluştur
sio = socketio.AsyncServer(
    cors_allowed_origins="*",  # Tüm origin'lere izin ver (production'da kısıtla)
    async_mode='aiohttp'
)

# HTTP app oluştur
app = web.Application()
sio.attach(app)

# Global state: Odalar ve oda kodları
rooms: dict[str, GameRoom] = {}  # room_id -> GameRoom
room_codes: dict[str, str] = {}  # room_code -> room_id

# Handler'ları oluştur
room_handlers = RoomHandlers(rooms, room_codes)
game_handlers = GameHandlers(rooms)


# ==================== Connection Events ====================

@sio.event
async def connect(sid: str, environ: dict, auth: dict) -> None:
    """Client bağlandığında."""
    logger.info(f"Client connected: {sid}")


@sio.event
async def disconnect(sid: str) -> None:
    """Client bağlantısı koptuğunda."""
    logger.info(f"Client disconnected: {sid}")
    
    # Oyuncunun bulunduğu odayı bul
    room = room_handlers.find_player_room_by_socket(sid)
    if room:
        # İlk oyuncu (odayı oluşturan) mu kontrol et
        is_room_creator = len(room.players) > 0 and room.players[0].socket_id == sid
        
        # Oyuncuyu odadan çıkar
        result = room_handlers.handle_leave_room(sid)
        
        if result:
            room_id = result.get("room_id") or room.room_id
            room_code = result.get("room_code") or room.room_code
            
            # Socket.io room'dan çıkar
            await sio.leave_room(sid, room_id)
            
            # Eğer odayı oluşturan oyuncu çıktıysa veya oda boşsa, odayı tamamen sil
            if is_room_creator or result.get("room_deleted", False):
                logger.info(f"Room creator left, deleting room {room_code}")
                # In-memory cache'den sil
                if room.room_id in rooms:
                    del rooms[room.room_id]
                if room_code in room_codes:
                    del room_codes[room_code]
                
                # KRİTİK: Oyun başladıysa, diğer oyuncuya oyunun bittiğini bildir
                message = "Oda oluşturan oyuncu çıktı, oda silindi"
                if room.started:
                    message = "Oyun sırasında oyuncu çıktı, oyun sonlandı"
                
                # Odadaki diğer oyunculara oda silindi mesajı gönder
                await sio.emit("room_deleted", {
                    "type": "room_deleted",
                    "room_code": room_code,
                    "message": message,
                    "game_ended": room.started  # Oyun başladıysa True
                }, room=room_id)
            else:
                # Odadaki diğer oyunculara oyuncu çıktı mesajı gönder
                await sio.emit("player_left", result, room=room_id)


# ==================== Room Events ====================

@sio.event
async def create_room(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Yeni oda oluştur.
    
    Expected data:
        {
            "username": "Player1"
        }
    """
    try:
        username = data.get("username", f"Player_{sid[:8]}")
        
        result = room_handlers.handle_create_room(sid, username)
        
        if result["type"] == "room_created":
            # Oyuncuyu odaya join et (socket.io room)
            room_id = result["room_id"]
            await sio.enter_room(sid, room_id)
            logger.info(f"Player {username} joined socket.io room {room_id}")
            
            # In-memory cache'e ekle (eğer yoksa)
            if room_id not in rooms:
                room = room_handlers.rooms.get(room_id)
                if room:
                    rooms[room_id] = room
                    room_codes[room.room_code] = room_id
            
            # Client'a response gönder
            await sio.emit("room_created", result, room=sid)
            
            # Tüm client'lara oda listesini güncelle (broadcast)
            # Yeni oda oluşturuldu, herkes listeyi yenilesin
            try:
                list_result = await list_rooms(sid, {})
                # Tüm bağlı client'lara gönder
                # Python socketio'da broadcast için skip_sid parametresini kullanmıyoruz
                # Tüm namespace'deki tüm client'lara göndermek için room=None kullanıyoruz
                await sio.emit("rooms_list", list_result, room=None)
            except Exception as e:
                logger.warning(f"Failed to broadcast room list update: {e}")
        
        return result
    except Exception as e:
        logger.error(f"Error in create_room: {e}", exc_info=True)
        error_result = {
            "type": "error",
            "message": f"Oda oluşturulamadı: {str(e)}"
        }
        await sio.emit("error", error_result, room=sid)
        return error_result


@sio.event
async def list_rooms(sid: str, data: dict[str, Any] = None) -> dict[str, Any]:
    """
    Aktif odaları listele - Hem PostgreSQL hem in-memory cache'den.
    
    Returns:
        {
            "type": "rooms_list",
            "rooms": [
                {
                    "room_code": "ABC123",
                    "level_id": "level_1",
                    "player_count": 1,
                    "max_players": 2
                },
                ...
            ]
        }
    """
    try:
        rooms_data = []
        
        # PostgreSQL'den direkt oku - BASIT SELECT
        try:
            from repository.room_repository import RoomRepository
            repo = RoomRepository()
            active_rooms = repo.list_active_rooms()
            
            logger.info(f"📋 PostgreSQL'den {len(active_rooms)} aktif oda bulundu")
            
            for room in active_rooms:
                rooms_data.append({
                    "room_code": room.room_code,
                    "level_id": room.level_id,
                    "player_count": len(room.players),
                    "max_players": 2,
                    "started": room.started
                })
                # In-memory cache'i de güncelle
                if room.room_id not in rooms:
                    rooms[room.room_id] = room
                    room_codes[room.room_code] = room.room_id
                    logger.debug(f"✅ Room {room.room_code} added to cache")
        except Exception as db_error:
            logger.error(f"❌ PostgreSQL hatası: {db_error}", exc_info=True)
            # Fallback: in-memory cache'den oku
            logger.warning("⚠️ PostgreSQL'den okuyamadı, in-memory cache kullanılıyor")
            for room_id, room in rooms.items():
                if not room.started and len(room.players) < 2:
                    rooms_data.append({
                        "room_code": room.room_code,
                        "level_id": room.level_id,
                        "player_count": len(room.players),
                        "max_players": 2,
                        "started": room.started
                    })
        
        result = {
            "type": "rooms_list",
            "rooms": rooms_data
        }
        
        logger.info(f"📤 {len(rooms_data)} oda gönderiliyor (client: {sid[:8]})")
        await sio.emit("rooms_list", result, room=sid)
        return result
    except Exception as e:
        logger.error(f"Error in list_rooms: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Oda listesi alınamadı: {str(e)}"
        }


@sio.event
async def join_room(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Odaya katıl.
    
    Expected data:
        {
            "username": "Player2",
            "room_code": "ABC123"
        }
    """
    try:
        username = data.get("username", f"Player_{sid[:8]}")
        room_code = data.get("room_code", "").strip().upper()
        
        result = room_handlers.handle_join_room(sid, username, room_code)
        
        if result["type"] == "player_joined":
            # Oyuncuyu odaya join et (socket.io room)
            room_id = room_codes.get(room_code)
            if room_id:
                await sio.enter_room(sid, room_id)
                logger.info(f"Player {username} joined socket.io room {room_id}")
                
                # Odadaki tüm oyunculara bildir
                await sio.emit("player_joined", result, room=room_id)
                
                # Oda doluysa oyunu başlat
                room = rooms.get(room_id)
                if room and room.is_full():
                    game_started = game_handlers.start_game(room_id)
                    if game_started:
                        await sio.emit("game_started", game_started, room=room_id)
                        logger.info(f"Game started in room {room_id}")
            
            # Katılan oyuncuya da response gönder
            await sio.emit("player_joined", result, room=sid)
            return result
        else:
            # Hata durumu - client'a error gönder
            await sio.emit("error", result, room=sid)
            return result
    except Exception as e:
        logger.error(f"Error in join_room: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Odaya katılamadı: {str(e)}"
        }


@sio.event
async def leave_room(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Odadan çık.
    
    Expected data: {} (boş olabilir)
    """
    try:
        result = room_handlers.handle_leave_room(sid)
        
        if result:
            # Socket.io room'dan çık
            room = room_handlers.get_room_by_socket(sid)
            if room:
                await sio.leave_room(sid, room.room_id)
                # Odadaki diğer oyunculara bildir
                await sio.emit("player_left", result, room=room.room_id)
            
            return result
        else:
            return {
                "type": "error",
                "message": "Aktif oda bulunamadı"
            }
    except Exception as e:
        logger.error(f"Error in leave_room: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Odadan çıkılamadı: {str(e)}"
        }


# ==================== Game Events ====================

@sio.event
async def player_move(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Oyuncu hareket.
    
    Expected data:
        {
            "direction": "up"  // "up", "down", "left", "right"
        }
    """
    try:
        direction = data.get("direction", "")
        
        if direction not in ["up", "down", "left", "right"]:
            return {
                "type": "error",
                "message": "Geçersiz yön"
            }
        
        game_state = game_handlers.handle_player_move(sid, direction)
        
        if game_state:
            # Odadaki tüm oyunculara IMMEDIATE state gönder (SERVER AUTHORITATIVE)
            # Her hareket sonrası anında state broadcast - client-side prediction yok
            room = game_handlers.find_player_room(sid)
            if room:
                await sio.emit("game_state", game_state, room=room.room_id)
            
            return {"type": "ok"}
        else:
            return {
                "type": "error",
                "message": "Aktif oyun bulunamadı"
            }
    except Exception as e:
        logger.error(f"Error in player_move: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Hareket işlenemedi: {str(e)}"
        }


@sio.event
async def player_damage(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Oyuncu hasar aldı (düşman hasarı için).
    
    Expected data:
        {
            "damage": 10  // Hasar miktarı
        }
    """
    try:
        damage = data.get("damage", 0)
        
        if damage <= 0:
            return {
                "type": "error",
                "message": "Geçersiz hasar miktarı"
            }
        
        room = game_handlers.find_player_room(sid)
        if not room:
            return {
                "type": "error",
                "message": "Aktif oyun bulunamadı"
            }
        
        player = room.get_player_by_socket(sid)
        if not player:
            return {
                "type": "error",
                "message": "Oyuncu bulunamadı"
            }
        
        # Hasarı uygula
        player.health = max(0, player.health - damage)
        logger.info(f"Player {player.username} took {damage} damage from enemy, health: {player.health}")
        
        # Game state'i güncelle ve gönder
        game_state = game_handlers.get_game_state(room.room_id)
        if game_state:
            await sio.emit("game_state", game_state, room=room.room_id)
        
        return {"type": "ok"}
    except Exception as e:
        logger.error(f"Error in player_damage: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Hasar işlenemedi: {str(e)}"
        }


@sio.event
async def place_bomb(sid: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Bomba koy.
    
    Expected data: {} (boş olabilir)
    """
    try:
        game_state = game_handlers.handle_place_bomb(sid)
        
        if game_state:
            # Odadaki tüm oyunculara IMMEDIATE state gönder (SERVER AUTHORITATIVE)
            # Bomba koyulduğunda anında state broadcast
            room = game_handlers.find_player_room(sid)
            if room:
                await sio.emit("game_state", game_state, room=room.room_id)
            
            return {"type": "ok"}
        else:
            return {
                "type": "error",
                "message": "Aktif oyun bulunamadı"
            }
    except Exception as e:
        logger.error(f"Error in place_bomb: {e}", exc_info=True)
        return {
            "type": "error",
            "message": f"Bomba yerleştirilemedi: {str(e)}"
        }


# ==================== Background Tasks ====================

async def game_loop() -> None:
    """Oyun güncelleme loop'u - bombalar, patlamalar, vb. (SERVER AUTHORITATIVE)"""
    while True:
        try:
            await asyncio.sleep(0.033)  # ~30 FPS güncelleme (daha responsive, düşük latency)
            delta = 0.033
            
            # Tüm aktif odaları güncelle - game_handlers.rooms kullan (global rooms ile senkronize)
            for room_id, room in list(game_handlers.rooms.items()):  # game_handlers.rooms kullan
                if room.started:
                    game_state = game_handlers.update_game(room_id, delta)
                    if game_state:
                        # Odadaki tüm oyunculara güncellenmiş state gönder (SERVER AUTHORITATIVE)
                        # Her frame'de state gönder - client-side prediction yok
                        await sio.emit("game_state", game_state, room=room_id)
                        # Debug: Bomba varsa logla
                        if room.bombs:
                            logger.debug(f"Room {room_id}: {len(room.bombs)} bombs, {sum(1 for b in room.bombs if not b.exploded)} active")
        except Exception as e:
            logger.error(f"Error in game loop: {e}", exc_info=True)


# ==================== Main ====================

def main() -> None:
    """Server'ı başlat."""
    port = 7777
    logger.info(f"🚀 Bomberman Multiplayer Server starting on port {port}")
    logger.info(f"📊 PostgreSQL connection: {POSTGRESQL_CONNECTION_STRING[:50]}...")
    
    # PostgreSQL bağlantısını test et
    try:
        from repository.room_repository import RoomRepository
        repo = RoomRepository()
        # Test query
        repo.list_active_rooms()
        logger.info("✅ PostgreSQL connection successful!")
    except Exception as e:
        logger.warning(f"⚠️ PostgreSQL connection test failed: {e}")
        logger.warning("Server will continue but rooms won't be persisted to database")
    
    logger.info("✅ Server ready!")
    
    # Background task başlat (game loop)
    async def start_background_tasks(app):
        asyncio.create_task(game_loop())
    
    app.on_startup.append(start_background_tasks)
    
    web.run_app(app, port=port, host="0.0.0.0")


if __name__ == "__main__":
    main()

