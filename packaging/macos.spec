# macOS-targeted PyInstaller spec (adjust signing/notarization externally)

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['PyQt6', 'pystray', 'PIL', 'numpy', 'sounddevice', 'faster_whisper', 'torch'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = BUNDLE(
    exe=EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=False,
        name='VoiceKeyboard',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='packaging/icon.icns',
    ),
    name='VoiceKeyboard.app',
    icon='packaging/icon.icns',
    bundle_identifier='com.example.voicekeyboard',
)
coll = COLLECT(
    app,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VoiceKeyboard')

