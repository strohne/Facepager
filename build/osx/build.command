#!/bin/sh

cd "`dirname "$0"`"
cd ../../src
python setup_osx.py py2app

cd dist
zip -r Facepager.app.zip Facepager.app
cp Facepager.app.zip ../../build/osx/Facepager_3_10.app.zip

read -p "Press any key to continue..." -n1 -s
