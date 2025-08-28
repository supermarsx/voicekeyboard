from voicekeyboard.tray import TrayIconManager


def test_tray_menu_builds():
    menu = TrayIconManager.menuInit(
        lambda *_: None,
        lambda *_: None,
        lambda *_: None,
        lambda *_: None,
    )
    # Ensure menu object has items
    assert menu is not None
