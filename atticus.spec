# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the downloadable Atticus Windows app.
# Build on Windows:  powershell -File scripts\build_windows_app.ps1

block_cipher = None

a = Analysis(
    ['atticus/launcher.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('atticus/api/static/retro', 'atticus/api/static/retro'),
        ('config/atticus.example.yaml', 'config'),
        ('prompts', 'prompts'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'webview',
        'atticus.api.app',
        'atticus.api_server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Atticus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
