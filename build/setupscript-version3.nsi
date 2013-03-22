; Start

Name "Facepager 3"
CRCCheck On

;——————————–
;General

OutFile "Facepager_Setup_3_0.exe"
ShowInstDetails "nevershow"
ShowUninstDetails "nevershow"

;——————————–
;Include Modern UI

!include "MUI2.nsh"
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\icon_facepager.ico"

;——————————–
;Interface Settings

!define MUI_ABORTWARNING

;——————————–
;Pages


;!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Facepager.exe"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;——————————–
;Languages

!insertmacro MUI_LANGUAGE "English"

;——————————–
;Folder selection page

InstallDir "$PROGRAMFILES\Facepager"

;——————————–
;Data



;——————————–
;Installer Sections
Section "Facepager" Install

;Add files
SetOutPath "$INSTDIR"

File "exe.win32-2.7\Facepager.exe"
File "exe.win32-2.7\bz2.pyd"
File "exe.win32-2.7\library.zip"
File "exe.win32-2.7\mfc90.dll"
File "exe.win32-2.7\pyexpat.pyd"
File "exe.win32-2.7\pyside-python2.7.dll"
File "exe.win32-2.7\PySide.QtCore.pyd"
File "exe.win32-2.7\PySide.QtGui.pyd"
File "exe.win32-2.7\PySide.QtNetwork.pyd"
File "exe.win32-2.7\PySide.QtWebKit.pyd"
File "exe.win32-2.7\python27.dll"
File "exe.win32-2.7\pythoncom27.dll"
File "exe.win32-2.7\pywintypes27.dll"
File "exe.win32-2.7\QtCore4.dll"
File "exe.win32-2.7\QtGui4.dll"
File "exe.win32-2.7\QtNetwork4.dll"
File "exe.win32-2.7\QtWebKit4.dll"
File "exe.win32-2.7\shiboken-python2.7.dll"
File "exe.win32-2.7\sqlite3.dll"
File "exe.win32-2.7\unicodedata.pyd"
File "exe.win32-2.7\win32api.pyd"
File "exe.win32-2.7\win32pipe.pyd"
File "exe.win32-2.7\win32ui.pyd"
File "exe.win32-2.7\win32wnet.pyd"
File "exe.win32-2.7\_ctypes.pyd"
File "exe.win32-2.7\_hashlib.pyd"
File "exe.win32-2.7\_socket.pyd"
File "exe.win32-2.7\_sqlite3.pyd"
File "exe.win32-2.7\_ssl.pyd"
File "exe.win32-2.7\ssleay32.dll"
File "exe.win32-2.7\libeay32.dll"

SetOutPath "$INSTDIR\help"
File "exe.win32-2.7\help\help.html"

;CreateDirectory "$INSTDIR\help"
;CopyFiles "${NSISDIR}\Plugins\*.*" "C:\TEMP\test"

;create desktop shortcut
CreateShortCut "$DESKTOP\Facepager.lnk" "$INSTDIR\Facepager.exe" ""

;create start-menu items
CreateDirectory "$SMPROGRAMS\Facepager"
CreateShortCut "$SMPROGRAMS\Facepager\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
CreateShortCut "$SMPROGRAMS\Facepager\Facepager.lnk" "$INSTDIR\Facepager.exe" "" "$INSTDIR\Pacepager.exe" 0

;write uninstall information to the registry
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Facepager" "DisplayName" "Facepager(remove only)"
WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Facepager" "UninstallString" "$INSTDIR\Uninstall.exe"

WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

;——————————–
;Uninstaller Section
Section "Uninstall"

;Delete Files
RMDir /r "$INSTDIR\*.*"

;Remove the installation directory
RMDir "$INSTDIR"

;Delete Start Menu Shortcuts
Delete "$DESKTOP\Facepager.lnk"
Delete "$SMPROGRAMS\Facepager\*.*"
RmDir  "$SMPROGRAMS\Facepager"

;Delete Uninstaller And Unistall Registry Entries
DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Facepager"
DeleteRegKey HKEY_LOCAL_MACHINE "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Facepager"

SectionEnd
