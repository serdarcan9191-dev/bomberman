# Backend UML Diagramları

Bu dosya backend mimarisinin UML diagramlarını içerir. PlantUML formatında yazılmıştır.

## PlantUML Kullanımı

PlantUML diagramlarını görüntülemek için:
1. **Online**: [PlantUML Server](http://www.plantuml.com/plantuml/uml/) adresine gidin ve kodları yapıştırın
2. **VS Code**: PlantUML extension'ı yükleyin
3. **GitHub**: GitHub otomatik olarak PlantUML diagramlarını render eder (markdown içinde)

---

## 1. Class Diagram - Repository Pattern

Repository Pattern'in class diagram'ı. `RoomRepository` ve `GameRoom` arasındaki ilişkiyi gösterir.

```plantuml
@startuml Backend_Repository_Pattern_Class_Diagram

package "backend.models" {
    class GameRoom {
        - room_id: str
        - room_code: str
        - players: list[Player]
        - started: bool
        - level_id: str
        - level_width: int
        - level_height: int
        - level_data: Optional[LevelData]
        - bombs: list[Bomb]
        - enemies: list[Enemy]
        + is_full(): bool
        + add_player(player: Player): bool
        + remove_player(player_id: str): Optional[Player]
        + get_player(player_id: str): Optional[Player]
        + get_player_by_socket(socket_id: str): Optional[Player]
    }
    
    class Player {
        - player_id: str
        - username: str
        - socket_id: str
        - position: tuple[int, int]
        - health: int
        - ready: bool
        - bomb_power: int
        - bomb_count: int
        - reached_exit: bool
        + to_dict(): dict
    }
    
    class Bomb {
        - x: int
        - y: int
        - player_id: str
        - timer: float
        - exploded: bool
        - explosion_timer: float
        - explosion_tiles: list[tuple[int, int]]
    }
    
    class Enemy {
        - enemy_id: str
        - enemy_type: str
        - position: tuple[int, int]
        - spawn_position: tuple[int, int]
        - health: int
        - alive: bool
        - last_move_time: float
        + to_dict(): dict
    }
    
    GameRoom "1" *-- "0..*" Player : contains
    GameRoom "1" *-- "0..*" Bomb : contains
    GameRoom "1" *-- "0..*" Enemy : contains
}

package "backend.repository" {
    class RoomRepository {
        - connection_string: str
        + __init__()
        - _get_connection()
        + create_room(room: GameRoom): bool
        + get_room_by_code(room_code: str): Optional[GameRoom]
        + get_room_by_id(room_id: str): Optional[GameRoom]
        + update_room(room: GameRoom): bool
        + delete_room(room_id: str): bool
        + add_player_to_room(room_id: str, player: Player): bool
        + remove_player_from_room(room_id: str, player_id: str): bool
        + list_active_rooms(): List[GameRoom]
        + room_code_exists(room_code: str): bool
    }
}

package "backend.handlers" {
    class RoomHandlers {
        - rooms: dict[str, GameRoom]
        - room_codes: dict[str, str]
        - repository: RoomRepository
        + handle_create_room(socket_id: str, username: str): dict
        + handle_join_room(socket_id: str, username: str, room_code: str): dict
        + handle_leave_room(socket_id: str): dict
        + handle_list_rooms(): dict
        - find_player_room_by_socket(socket_id: str): Optional[GameRoom]
    }
    
    class GameHandlers {
        - rooms: dict[str, GameRoom]
        - repository: RoomRepository
        - setup_service: GameSetupService
        - movement_service: GameMovementService
        - state_service: GameStateService
        - query_service: GameQueryService
        - start_service: GameStartService
        - update_service: GameUpdateService
        + handle_player_move(socket_id: str, direction: str): Optional[dict]
        + handle_place_bomb(socket_id: str): Optional[dict]
        + handle_player_ready(socket_id: str): Optional[dict]
    }
}

package "backend.services" {
    class GameSetupService {
        + setup_level(room: GameRoom, level_id: str): bool
        + spawn_enemies(room: GameRoom): None
    }
    
    class GameStartService {
        - setup_service: GameSetupService
        - repository: RoomRepository
        + start_game(room: GameRoom): bool
    }
}

database "PostgreSQL" {
    entity "rooms" {
        * room_id : VARCHAR
        * room_code : VARCHAR
        * level_id : VARCHAR
        * level_width : INT
        * level_height : INT
        * started : BOOLEAN
    }
    
    entity "room_players" {
        * room_id : VARCHAR
        * player_id : VARCHAR
        * username : VARCHAR
        * socket_id : VARCHAR
        * position_x : INT
        * position_y : INT
        * health : INT
        * ready : BOOLEAN
    }
}

RoomRepository ..> GameRoom : uses
RoomRepository ..> Player : uses
RoomHandlers --> RoomRepository : uses
GameHandlers --> RoomRepository : uses
GameHandlers --> GameSetupService : uses
GameStartService --> GameSetupService : uses
GameStartService --> RoomRepository : uses
RoomRepository ..> "rooms" : queries
RoomRepository ..> "room_players" : queries

note right of RoomRepository
    **Repository Pattern**
    Veri erişim mantığını
    iş mantığından ayırır.
    SOLID - Dependency Inversion
end note

@enduml
```

---

## 2. Component Diagram - Backend Mimarisi

Backend'in genel mimari yapısını gösterir.

```plantuml
@startuml Backend_Component_Diagram

package "Client" {
    [Socket.io Client]
}

package "Backend Server" {
    component [Socket.io Server] as Server {
        [Event Handlers]
    }
    
    component [Room Handlers] as RoomHandlers {
        [handle_create_room]
        [handle_join_room]
        [handle_leave_room]
        [handle_list_rooms]
    }
    
    component [Game Handlers] as GameHandlers {
        [handle_player_move]
        [handle_place_bomb]
        [handle_player_ready]
    }
    
    component [Services] as Services {
        [GameSetupService]
        [GameMovementService]
        [GameStateService]
        [GameQueryService]
        [GameStartService]
        [GameUpdateService]
    }
    
    component [Repository] as Repository {
        [RoomRepository]
    }
    
    database "PostgreSQL" {
        [rooms table]
        [room_players table]
    }
}

[Socket.io Client] --> [Socket.io Server] : WebSocket Connection
[Socket.io Server] --> [Room Handlers] : routes room events
[Socket.io Server] --> [Game Handlers] : routes game events
[Room Handlers] --> [Repository] : data access
[Game Handlers] --> [Repository] : data access
[Game Handlers] --> [Services] : business logic
[Repository] --> [rooms table] : SQL queries
[Repository] --> [room_players table] : SQL queries

note right of Repository
    **Repository Pattern**
    Veri erişim katmanı
    İş mantığından bağımsız
end note

note right of Services
    **Service Layer**
    İş mantığı
    SOLID - Single Responsibility
end note

@enduml
```

---

## 3. Sequence Diagram - Room Oluşturma Akışı

Bir oyuncunun oda oluşturma sürecini gösterir.

```plantuml
@startuml Backend_Room_Creation_Sequence

actor "Client" as Client
participant "Socket.io Server" as Server
participant "RoomHandlers" as Handler
participant "RoomRepository" as Repository
database "PostgreSQL" as DB

Client -> Server: create_room(username)
activate Server

Server -> Handler: handle_create_room(socket_id, username)
activate Handler

Handler -> Handler: find_player_room_by_socket(socket_id)
Handler -> Handler: generate_room_code()
Handler -> Handler: create GameRoom instance
Handler -> Handler: create Player instance
Handler -> Handler: add player to room (in-memory)

Handler -> Repository: create_room(room)
activate Repository

Repository -> Repository: _get_connection()
Repository -> DB: INSERT INTO rooms (...)
activate DB
DB --> Repository: success
deactivate DB

Repository -> DB: INSERT INTO room_players (...)
activate DB
DB --> Repository: success
deactivate DB

Repository --> Handler: true
deactivate Repository

Handler -> Handler: update in-memory cache
Handler --> Server: {type: "room_created", room_code: "ABC123", ...}
deactivate Handler

Server --> Client: emit("room_created", response)
deactivate Server

note right of Repository
    **Repository Pattern**
    Veritabanı işlemleri
    Handler'dan ayrılmış
end note

@enduml
```

---

## 4. Sequence Diagram - Oyun Başlatma Akışı

İki oyuncu hazır olduğunda oyunun başlatılmasını gösterir.

```plantuml
@startuml Backend_Game_Start_Sequence

participant "Client 1" as C1
participant "Client 2" as C2
participant "Socket.io Server" as Server
participant "GameHandlers" as Handler
participant "GameStartService" as StartService
participant "GameSetupService" as SetupService
participant "RoomRepository" as Repository
database "PostgreSQL" as DB

C1 -> Server: player_ready()
C2 -> Server: player_ready()

Server -> Handler: handle_player_ready(socket_id)
activate Handler

Handler -> Handler: get room and player
Handler -> Handler: set player.ready = true

alt Both players ready
    Handler -> StartService: start_game(room)
    activate StartService
    
    StartService -> SetupService: setup_level(room, level_id)
    activate SetupService
    SetupService -> SetupService: load level data
    SetupService -> SetupService: spawn enemies
    SetupService --> StartService: success
    deactivate SetupService
    
    StartService -> Repository: update_room(room)
    activate Repository
    Repository -> DB: UPDATE rooms SET started = true
    activate DB
    DB --> Repository: success
    deactivate DB
    Repository --> StartService: true
    deactivate Repository
    
    StartService --> Handler: true
    deactivate StartService
    
    Handler -> Server: broadcast game_started
    Server --> C1: emit("game_started", game_state)
    Server --> C2: emit("game_started", game_state)
else Not all ready
    Handler -> Server: broadcast player_ready
    Server --> C1: emit("player_ready", player_data)
    Server --> C2: emit("player_ready", player_data)
end

Handler --> Server: response
deactivate Handler

note right of StartService
    **Service Layer Pattern**
    İş mantığı ayrılmış
    SOLID - Single Responsibility
end note

@enduml
```

---

## 5. Class Diagram - Service Layer

Service katmanının detaylı class diagram'ı.

```plantuml
@startuml Backend_Service_Layer_Class_Diagram

package "backend.services" {
    class GameSetupService {
        + setup_level(room: GameRoom, level_id: str): bool
        + spawn_enemies(room: GameRoom): None
        - _load_level_data(level_id: str): Optional[LevelData]
    }
    
    class GameMovementService {
        + can_move(room: GameRoom, player: Player, direction: str): bool
        + move_player(room: GameRoom, player: Player, direction: str): bool
        + check_collision(room: GameRoom, x: int, y: int): bool
    }
    
    class GameStateService {
        + serialize_game_state(room: GameRoom): dict
        + deserialize_game_state(data: dict): GameRoom
    }
    
    class GameQueryService {
        - rooms: dict[str, GameRoom]
        + get_room_by_socket(socket_id: str): Optional[GameRoom]
        + get_player_by_socket(socket_id: str): Optional[tuple[GameRoom, Player]]
    }
    
    class GameStartService {
        - setup_service: GameSetupService
        - repository: RoomRepository
        + start_game(room: GameRoom): bool
    }
    
    class GameUpdateService {
        - movement_service: GameMovementService
        - state_service: GameStateService
        - setup_service: GameSetupService
        + update_game(room: GameRoom, delta_time: float): None
        + update_bombs(room: GameRoom, delta_time: float): None
        + update_enemies(room: GameRoom, delta_time: float): None
    }
    
    class BombService {
        + place_bomb(room: GameRoom, player: Player): bool
        + explode_bomb(room: GameRoom, bomb: Bomb): None
        + check_explosion_collision(room: GameRoom, x: int, y: int): bool
    }
    
    class EnemyDamageService {
        + check_enemy_damage(room: GameRoom, explosion_tiles: list): None
        + kill_enemy(room: GameRoom, enemy: Enemy): None
    }
}

package "backend.models" {
    class GameRoom {
        + room_id: str
        + players: list[Player]
        + bombs: list[Bomb]
        + enemies: list[Enemy]
    }
}

package "backend.repository" {
    class RoomRepository {
        + update_room(room: GameRoom): bool
    }
}

GameSetupService --> GameRoom : uses
GameMovementService --> GameRoom : uses
GameStateService --> GameRoom : uses
GameQueryService --> GameRoom : uses
GameStartService --> GameSetupService : uses
GameStartService --> RoomRepository : uses
GameUpdateService --> GameMovementService : uses
GameUpdateService --> GameStateService : uses
GameUpdateService --> GameSetupService : uses
BombService --> GameRoom : uses
EnemyDamageService --> GameRoom : uses

note right of GameSetupService
    **Service Layer Pattern**
    Her service tek bir
    sorumluluğa sahip
    SOLID - Single Responsibility
end note

@enduml
```

---

## Diagram Kullanım Notları

### PlantUML Render Etme

1. **VS Code ile**:
   - PlantUML extension yükleyin
   - `.puml` dosyası oluşturun veya markdown içindeki kodları kopyalayın
   - Preview yapın

2. **Online**:
   - [PlantUML Server](http://www.plantuml.com/plantuml/uml/) adresine gidin
   - Kodları yapıştırın ve görüntüleyin

3. **GitHub**:
   - GitHub otomatik olarak markdown içindeki PlantUML kodlarını render eder
   - Sadece ` ```plantuml ` bloğu kullanın

4. **PNG Export**:
   - PlantUML Server'da "PNG" butonuna tıklayın
   - Veya VS Code extension ile export edin

### Diagram Açıklamaları

- **Class Diagram**: Sınıflar, özellikler, metodlar ve ilişkileri gösterir
- **Component Diagram**: Sistem bileşenleri ve aralarındaki bağımlılıkları gösterir
- **Sequence Diagram**: Zaman içindeki mesaj akışını gösterir

---

## SOLID Prensipleri ve UML

Bu diagramlar SOLID prensiplerine uygun yapıyı gösterir:

- ✅ **Single Responsibility**: Her sınıf/service tek bir sorumluluğa sahip
- ✅ **Dependency Inversion**: Repository Pattern ile veri erişimi soyutlanmış
- ✅ **Open/Closed**: Yeni repository implementasyonu eklemek kolay

---

**Not**: Bu diagramlar backend mimarisini ve Repository Pattern kullanımını gösterir. Design document'te bu diagramları kullanabilirsiniz.

