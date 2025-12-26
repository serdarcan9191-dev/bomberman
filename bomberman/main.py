"""
Oyunu başlatmak için basit bir giriş noktası.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pygame

# Logging ayarları - INFO level'da tüm loglar görünsün
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from config.database import POSTGRESQL_CONNECTION_STRING
from controller.game_controller import GameController
from service.auth_service import AuthService
from service.sound_service import SoundService
from service.user_progress_service import UserProgressService
from view.gallery_screen import GalleryScreen
from view.game_scene import GameScene
from view.login_screen import LoginScreen
from view.loading_scene import LoadingScene
from view.multiplayer_lobby import MultiplayerLobbyScreen
from view.register_screen import RegisterScreen
from view.main_menu import MenuOption, StartScreen, MenuTheme
from view.pygame_view import PygameView, ViewConfig
from view.scene_manager import SceneManager


def _exit_app() -> None:
    pygame.event.post(pygame.event.Event(pygame.QUIT))


def _start_game(
    controller: GameController,
    scene: GameScene,
    manager: SceneManager,
    loading_scene: LoadingScene,
    progress_service: UserProgressService,
    auth_service: AuthService,
    is_new_game: bool = False,
) -> None:
    """Oyunu başlatır - önce loading ekranı gösterir"""
    # Loading tamamlandığında oyunu başlat
    def on_loading_complete():
        # Multiplayer state'ini temizle (single player'a geçiş için)
        if hasattr(scene, 'reset_multiplayer'):
            scene.reset_multiplayer()
        
        # Kullanıcının mevcut levelini belirle
        user_id = auth_service.get_current_user_id()
        
        # GameController'a user_id'yi set et
        controller.set_current_user_id(user_id)
        
        if is_new_game or not user_id:
            # Yeni oyun: level_1'den başla
            start_level = "level_1"
            if user_id:
                progress_service.reset_progress(user_id)
        else:
            # Devam et: kayıtlı leveldan başla
            start_level = progress_service.get_current_level(user_id) or "level_1"
        
        controller.load(start_level)
        manager.switch_to(scene)
    
    # Loading scene'e callback'i set et ve loading ekranına geç
    loading_scene.set_on_loaded(on_loading_complete)
    manager.switch_to(loading_scene)


def main() -> None:
    config = ViewConfig()
    view = PygameView(config)
    manager = SceneManager()

    view.initialize()
    pygame.font.init()
    pygame.mixer.init()

    # Sound Service oluştur
    assets_dir = Path(__file__).resolve().parent / "assets"
    sound_service = SoundService(assets_dir=assets_dir)

    # Arka plan müziğini başlat (theme.wav varsa)
    sound_service.play_music("theme.wav", loop=True, volume=0.4)

    # Auth Service oluştur - PostgreSQL bağlantısı ile
    auth_service = AuthService(db_connection_string=POSTGRESQL_CONNECTION_STRING)
    
    # User Progress Service oluştur
    progress_service = UserProgressService(db_connection_string=POSTGRESQL_CONNECTION_STRING)

    # Game Controller oluştur (all services with DI + SoundService + ProgressService)
    game_controller = GameController(sound_service=sound_service, progress_service=progress_service)

    # Game Scene oluştur
    game_scene = GameScene(game_controller, sound_service, exit_callback=manager.return_to_menu)
    
    # Theme helper function - kullanıcı tercihine göre theme döndürür
    def get_user_theme() -> MenuTheme:
        """Kullanıcının tercih ettiği theme'i döndürür."""
        if auth_service.get_current_user_id():
            theme_name = auth_service.get_user_preferred_theme()
            return MenuTheme.from_string(theme_name)
        return MenuTheme.default()
    
    # Loading scene oluştur ve SceneManager'a register et - theme ile
    loading_scene = LoadingScene(on_loaded=None, theme=get_user_theme())
    manager.set_loading_scene(loading_scene)
    
    # Theme güncelleme helper - tüm ekranları yeniden oluşturur
    def update_all_themes(new_theme: MenuTheme) -> None:
        """Tüm ekranların theme'ini günceller."""
        # StartScreen theme'ini güncelle
        if manager.menu and hasattr(manager.menu, '_theme'):
            manager.menu._theme = new_theme
        
        # Diğer ekranların theme'lerini güncelle
        if hasattr(gallery_screen, '_theme'):
            gallery_screen._theme = new_theme
        if hasattr(multiplayer_lobby, '_theme'):
            multiplayer_lobby._theme = new_theme
        if hasattr(login_screen, '_theme'):
            login_screen._theme = new_theme
        if hasattr(register_screen, '_theme'):
            register_screen._theme = new_theme
        if hasattr(loading_scene, '_theme'):
            loading_scene._theme = new_theme

    gallery_screen = GalleryScreen(manager, theme=get_user_theme())
    multiplayer_lobby = MultiplayerLobbyScreen(
        manager, 
        theme=get_user_theme(), 
        auth_service=auth_service,
        server_url="http://localhost:7777",
        game_controller=game_controller,
        game_scene=game_scene,
        loading_scene=loading_scene,
    )

    # Login ekranı (register callback'i sonra set edilecek)
    # Login başarılı olduğunda theme'i yükle
    def on_login_success():
        """Login başarılı olduğunda theme'i yükle ve menüye dön."""
        user_theme = get_user_theme()
        update_all_themes(user_theme)
        manager.return_to_menu(show_loading=True)
    
    login_screen = LoginScreen(
        manager,
        config=config,
        auth_service=auth_service,
        theme=MenuTheme.default(),  # İlk açılışta default, login sonrası güncellenecek
        on_success=on_login_success,
        on_register=None,  # Sonra set edilecek
    )

    # Kayıt ekranı: başarı/geri durumda login'e dön (loading ile)
    register_screen = RegisterScreen(
        manager,
        config=config,
        auth_service=auth_service,
        theme=get_user_theme(),
        on_success=lambda: manager.switch_to(login_screen, show_loading=True),
        on_cancel=lambda: manager.switch_to(login_screen, show_loading=True),
    )

    # Login ekranının register callback'ini ayarla (loading ile)
    login_screen._on_register = lambda: manager.switch_to(register_screen, show_loading=True)

    # Theme değiştirme fonksiyonu
    def toggle_theme() -> None:
        """Theme'i dark/light arasında değiştirir ve kaydeder."""
        if not auth_service.get_current_user_id():
            return  # Giriş yapılmamışsa theme değiştirilemez
        
        current_theme = auth_service.get_user_preferred_theme()
        new_theme_name = "light" if current_theme == "dark" else "dark"
        auth_service.set_user_preferred_theme(new_theme_name)
        
        new_theme = MenuTheme.from_string(new_theme_name)
        update_all_themes(new_theme)
        print(f"✅ Theme değiştirildi: {new_theme_name}")
        
        # Ekranı yeniden çiz (theme değişikliği hemen görünsün)
        # SceneManager zaten her frame'de draw() çağırıyor, bu yeterli

    options = [
        MenuOption(
            label="Devam Et",
            description="",
            action=lambda: _start_game(
                game_controller, game_scene, manager, loading_scene, 
                progress_service, auth_service, is_new_game=False
            ),
        ),
        MenuOption(
            label="Yeni Oyun",
            description="",
            action=lambda: _start_game(
                game_controller, game_scene, manager, loading_scene,
                progress_service, auth_service, is_new_game=True
            ),
        ),
        MenuOption(label="Çok Oyunculu", description="", action=lambda: manager.switch_to(multiplayer_lobby, show_loading=True)),
        MenuOption(label="Görseller", description="", action=lambda: manager.switch_to(gallery_screen, show_loading=True)),
        MenuOption(label="Tema Değiştir", description="", action=toggle_theme),
        MenuOption(label="Çıkış", description="", action=_exit_app),
    ]

    start_screen = StartScreen(config=config, options=options, theme=get_user_theme())
    manager.register_menu(start_screen)  # Menü referansı
    manager.set_initial(login_screen)    # İlk açılışta login gelsin

    try:
        view.render(manager, run_seconds=600.0)
    finally:
        view.shutdown()


if __name__ == "__main__":
    main()

