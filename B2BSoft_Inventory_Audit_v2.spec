# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['B2BSoft_Inventory_Audit_v2.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.edge',
        'selenium.webdriver.common',
        'selenium.webdriver.support',
        'selenium.webdriver.common.by',
        'bs4',
        'cryptography',
        'cryptography.fernet',
        'pandas',
        'openpyxl',
        'xlsxwriter',
        'pyautogui',
        'pynput',
        'apscheduler',
        'apscheduler.schedulers.background',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
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
    name='B2BSoft_Inventory_Audit_v2',
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
    icon='gfh_icon.ico',
)

collection = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='B2BSoft_Inventory_Audit_v2',
)
