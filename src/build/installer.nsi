
; Start

Name "Facepager"
CRCCheck On

;——————————–
;General

OutFile "Facepager_Setup.exe"
ShowInstDetails "nevershow"
ShowUninstDetails "nevershow"

;——————————–
;Include Modern UI

!include "MUI2.nsh"

;——————————–
;Interface Settings

!define MUI_ABORTWARNING

;——————————–
;Pages


!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

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

File "bin\Facepager.exe"
File "bin\_hashlib.pyd"
File "bin\_socket.pyd"
File "bin\_sqlite3.pyd"
File "bin\_ssl.pyd"
File "bin\bz2.pyd"
File "bin\library.zip"
File "bin\PySide.QtCore.pyd"
File "bin\pyexpat.pyd"
File "bin\PySide.QtGui.pyd"
File "bin\pyside-python2.7.dll"
File "bin\python27.dll"
File "bin\pywintypes27.dll"
File "bin\QtCore4.dll"
File "bin\QtGui4.dll"
File "bin\shiboken-python2.7.dll"
File "bin\sqlite3.dll"
File "bin\unicodedata.pyd"
File "bin\win32api.pyd"
File "bin\win32pipe.pyd"



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

