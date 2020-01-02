@rem setlocal
@rem ;SET PATH=%PATH%;C:\AndereProgramme\Python37
@rem ;set PYTHONPATH="C:\AndereProgramme\Python37\Lib;C:\AndereProgramme\Python37\DLLs"

cd ../../src
call "..\pyenv\Scripts\activate.bat"

rmdir /s / q build
rmdir /s / q dist

copy ..\build\windows\Facepager.spec Facepager.spec
pyinstaller --windowed --noconfirm Facepager.spec

cd dist
copy ..\..\build\windows\Facepager_Setupscript.nsi Facepager_Setupscript.nsi
"C:\Program Files (x86)\NSIS\makensis.exe" Facepager_Setupscript.nsi
copy Facepager_Setup.exe ..\..\build\windows\Facepager_Setup.exe 

endlocal
pause