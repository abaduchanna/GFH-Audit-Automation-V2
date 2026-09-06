# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['GFH_Audit_Automation.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['selenium', 'bs4', 'requests', 'pandas', 'openpyxl', 'pytesseract', 'PIL', 'cv2', 'cryptography'],
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
    name='GFH_Audit_Automation',
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
    icon=['gfh_icon.ico'],
)
