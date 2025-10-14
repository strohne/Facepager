# -*- mode: python -*-

block_cipher = None


a = Analysis(['Facepager.py'],
             pathex=['../src'],
             binaries=[],
             datas=[],
             hiddenimports=['PySide6.QtPrintSupport'],
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
          upx=True,
          console=False,
          icon='../icons/icon_facepager.icns',
          codesign_identity='PUT_HASH_OF_HASH_OF_INSTALLER_ID_HERE',
          entitlements_file='entitlements.plist')
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
             bundle_identifier='com.strohne.facepager')
