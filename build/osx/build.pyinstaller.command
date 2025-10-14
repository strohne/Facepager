#!/bin/sh

cd "`dirname "$0"`"
cd ../..

cp build/osx/entitlements.plist src/entitlements.plist
cp build/osx/Facepager.spec src/Facepager.spec

cd src
rm -rf build
rm -rf dist

source ../venv/bin/activate
../venv/bin/pyinstaller Facepager.spec
# cd ..
cd /dist

codesign -vv --strict Facepager.app

ditto -c -k --sequesterRsrc --keepParent Facepager.app Facepager.zip

xcrun notarytool submit Facepager.app --keychain-profile fpcodesign22 --wait
xcrun stapler staple Facepager.app
spctl -a -v Facepager.app

cd ../..

rm -rf Facepager_Setup_4_7_0.mac.pkg

productbuild --identifier "com.strohne.facepager.pkg" \
  --sign "AC630C1E0415944E2C2DCDE3210ADC5C8F20A02E" \
  --timestamp \
  --root src/dist/Facepager.app /Applications/Facepager.app \
  Facepager_Setup_4_7_0.mac.pkg

xcrun notarytool submit Facepager_Setup_4_7_0.mac.pkg --keychain-profile fpcodesign22 --wait
xcrun stapler staple Facepager_Setup_4_7_0.mac.pkg
spctl -a -vv -t install Facepager_Setup_4_7_0.mac.pkg
pkgutil --check-signature Facepager_Setup_4_7_0.mac.pkg

read -p "Press any key to continue..." -n1 -s
