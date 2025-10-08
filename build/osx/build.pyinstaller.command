#!/bin/sh

cd "`dirname "$0"`"
cd ../..

cp build/osx/Facepager.spec src/Facepager.spec
cp -r build/osx/hooks src/hooks

cd src
rm -rf build
rm -rf dist

source ../venv/bin/activate
../venv/bin/pyinstaller Facepager.spec
#../venv/bin/pyinstaller --onefile --windowed --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec
cd ..

python3 build/osx/fix_app_qt_folder_names_for_codesign.py src/dist/Facepager.app

codesign --deep --force --options=runtime --entitlements build/osx/entitlements.plist --sign "C5675C9047BC5F500D88849509790AEEBCB99534" --timestamp src/dist/Facepager.app

rm -rf build/osx/Facepager.pkg

productbuild --identifier "com.strohne.facepager.pkg" --sign "AC630C1E0415944E2C2DCDE3210ADC5C8F20A02E" --timestamp --root src/dist/Facepager.app /Applications/Facepager.app build/osx/Facepager.pkg

read -p "Press any key to continue..." -n1 -s