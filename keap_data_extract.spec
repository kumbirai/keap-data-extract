# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('src', 'src'), ('.env', '.'), ('logs', 'logs'), ('checkpoints', 'checkpoints')],
    hiddenimports=['sqlalchemy', 'psycopg2', 'alembic', 'dotenv', 'dateutil', 'dateutil.parser', 'dateutil.tz', 
                  'requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna',
                  'logging', 'logging.handlers', 'logging.config', 'logging.handlers.RotatingFileHandler'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='keap_data_extract',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.png'],
)
