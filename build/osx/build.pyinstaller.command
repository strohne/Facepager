#!/bin/sh

cd "`dirname "$0"`"
cp Facepager.spec ../../src/Facepager.spec

cd ../../src
rm -rf build
rm -rf dist

export DYLD_LIBRARY_PATH=/usr/local/lib/python2.7/site-packages/PySide
pyinstaller --onefile --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec

cd dist
zip -r Facepager.app.zip Facepager.app
cp Facepager.app.zip ../../build/osx/Facepager_3_10.app.zip
#cp Facepager ../../build/osx/Facepager_3_10

read -p "Press any key to continue..." -n1 -s