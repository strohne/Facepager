cd ../..
call "venv\Scripts\activate.bat"

cd src
rmdir /s / q build
rmdir /s / q dist

copy "..\build\windows\Facepager.spec" Facepager.spec

pyinstaller --noconfirm Facepager.spec
@rem pyinstaller --debug all --noconfirm --upx-exclude vcruntime140.dll Facepager.spec --upx-dir ..\build\windows\upx-3.96-win64\

cd dist
copy ..\..\build\windows\Facepager_Setupscript.nsi Facepager_Setupscript.nsi
copy ..\..\icons\icon_facepager.ico icon_facepager.ico
"C:\Program Files (x86)\NSIS\makensis.exe" Facepager_Setupscript.nsi
copy Facepager_Setup.exe ..\..\build\windows\Facepager_Setup.exe 

endlocal
pause