# -*- mode: python -*-

block_cipher = None


a = Analysis(['Facepager.py'],
             pathex=['/Users/devel/Documents/GitHub/Facepager/src'],
             binaries=[],
             datas=[('docs', 'docs'), ('ssl', 'ssl')],
             hiddenimports=['credentials'],
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
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False , icon='icon.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Facepager')
app = BUNDLE(coll,
             name='Facepager.app',
             icon='icon.icns',
             bundle_identifier=None)
