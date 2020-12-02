#!/bin/sh

cd "`dirname "$0"`"
cd ../../src

cp ../build/osx/Facepager.spec Facepager.spec
#cp -r ../build/osx/hooks hooks

rm -rf build
rm -rf dist

source ../pyenv/bin/activate
pyinstaller --windowed --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec

cd dist
zip -r Facepager.app.zip Facepager.app
cp Facepager.app.zip ../../build/osx/Facepager.app.zip

read -p "Press any key to continue..." -n1 -s