#!/bin/sh

cd "`dirname "$0"`"
cd ../../src

cp ../build/osx/Facepager.spec Facepager.spec
#cp -r ../build/osx/hooks hooks

rm -rf build
rm -rf dist

source ../venv/bin/activate
#../venv/bin/pyinstaller --onefile --windowed --noconfirm --upx-dir=/usr/local/bin/ Facepager.spec
../venv/bin/pyinstaller Facepager.spec

cd dist
zip -r Facepager.app.zip Facepager.app
cp Facepager.app.zip ../../build/osx/Facepager.app.zip

read -p "Press any key to continue..." -n1 -s