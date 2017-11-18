setlocal
SET PATH=%PATH%;C:\AndereProgramme\Python27
set PYTHONPATH="C:\AndereProgramme\Python27\Lib;C:\AndereProgramme\Python27\DLLs"

cd ../../src
python setup_windows.py build

cd build
copy Facepager.exe exe.win32-2.7
copy python27.dll exe.win32-2.7

copy ..\..\build\windows\Facepager_Setupscript.nsi exe.win32-2.7\Facepager_Setupscript.nsi
"C:\Program Files (x86)\NSIS\makensis.exe" exe.win32-2.7\Facepager_Setupscript.nsi
copy exe.win32-2.7\Facepager_Setup_3_9.exe ..\..\build\windows\Facepager_Setup_3_9.exe 

endlocal
pause