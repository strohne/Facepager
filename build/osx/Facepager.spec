# -*- mode: python -*-

block_cipher = None


a = Analysis(['Facepager.py'],
             pathex=['/Users/devel/Documents/GitHub/Facepager/src'],
             binaries=[],
             datas=[],
             hiddenimports=['credentials','PySide2.QtPrintSupport'],
             hookspath=['hooks'],
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
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False , icon='..\\icons\\icon_facepager.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Facepager')
app = BUNDLE(coll,
             name='Facepager.app',
             icon='../icons/icon_facepager.icns',
             bundle_identifier=None)
