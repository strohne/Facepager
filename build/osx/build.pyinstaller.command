#!/bin/sh

cd "`dirname "$0"`"
cp Facepager.spec ../../src/Facepager.spec

cd ../../src
rm -rf build
rm -rf dist

pyinstaller --windowed --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec

cd dist
zip -r Facepager.app.zip Facepager.app
cp Facepager.app.zip ../../build/osx/Facepager_4.app.zip

read -p "Press any key to continue..." -n1 -s