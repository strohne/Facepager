# -*- mode: python -*-

block_cipher = None


a = Analysis(['Facepager.py'],
             pathex=['.'],
             binaries=[('../build/windows/PySide2', 'PySide2'),('../build/windows/cchardet', 'cchardet'),('../pyenv/Lib/site-packages/pyjsparser','pyjsparser')],
             datas=[],
             hiddenimports=['PySide2.QtPrintSupport'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Facepager',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False , icon='..\\icons\\icon_facepager.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Facepager')
