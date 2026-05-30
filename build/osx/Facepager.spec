# -*- mode: python -*-

import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

block_cipher = None

def create_cipher(key):
    """Create an AES cipher object."""
    global block_cipher
    block_cipher = AES.new(key, AES.MODE_CBC)

def encrypt(data, key):
    """Encrypt data using AES encryption."""
    create_cipher(key)
    # Pad data to be multiple of block size
    padded_data = pad(data.encode(), AES.block_size)
    encrypted = block_cipher.encrypt(padded_data)
    return block_cipher.iv + encrypted  # Prepend IV for decryption

def decrypt(encrypted_data, key):
    """Decrypt data using AES encryption."""
    iv = encrypted_data[:AES.block_size]  # Extract IV from the beginning
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted_data[AES.block_size:]), AES.block_size)
    return decrypted.decode()

def main():
    key = os.urandom(16)  # AES key should be either 16, 24, or 32 bytes
    
    # User input for encryption
    data = input("Enter the data to encrypt: ")
    encrypted_data = encrypt(data, key)
    print(f"Encrypted: {encrypted_data.hex()}")  # Print as hex for readability

    # User input for decryption
    try:
        encrypted_hex = input("Enter the hex string to decrypt: ")
        encrypted_bytes = bytes.fromhex(encrypted_hex)
        decrypted_data = decrypt(encrypted_bytes, key)
        print(f"Decrypted: {decrypted_data}")
    except ValueError as e:
        print("Error during decryption:", e)

if __name__ == "__main__":
    main()


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
