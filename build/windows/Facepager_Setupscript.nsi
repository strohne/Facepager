; Start

Name "Facepager 3"
CRCCheck On

;General

OutFile "Facepager_Setup_3_10.exe"
ShowInstDetails "nevershow"
ShowUninstDetails "nevershow"

;覧覧覧覧覧・
;Include Modern UI

!include "MUI2.nsh"
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\icon_facepager.ico"

;覧覧覧覧覧・
;Interface Settings

!define MUI_ABORTWARNING

;覧覧覧覧覧・
;Pages


;!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\Facepager.exe"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;覧覧覧覧覧・
;Languages

!insertmacro MUI_LANGUAGE "English"

;覧覧覧覧覧・
;Folder selection page

InstallDir "$PROGRAMFILES\Facepager"

;覧覧覧覧覧・
;Data

;覧覧覧覧覧・
;Unistall Previous Section
; The "" makes the section hidden.
Section "" SecUninstallPrevious

    Call UninstallPrevious

SectionEnd

Function UninstallPrevious
    DetailPrint "Removing previous installation."    
    ; Run the uninstaller silently.
    ExecWait '"$INSTDIR\Uninstall.exe" /S _?=$INSTDIR'

FunctionEnd

;覧覧覧覧覧・
;Installer Sections
Section "Facepager" Install

;Add files
SetOutPath "$INSTDIR"

File "Facepager.exe"
File "bz2.pyd"
File "library.zip"
File "mfc90.dll"
File "pyexpat.pyd"
File "pyside-python2.7.dll"
File "PySide.QtCore.pyd"
File "PySide.QtGui.pyd"
File "PySide.QtNetwork.pyd"
File "PySide.QtWebKit.pyd"
File "python27.dll"
File "pythoncom27.dll"
File "pywintypes27.dll"
File "QtCore4.dll"
File "QtGui4.dll"
File "QtNetwork4.dll"
File "QtWebKit4.dll"
File "shiboken-python2.7.dll"
File "sqlite3.dll"
File "unicodedata.pyd"
File "win32api.pyd"
File "win32pipe.pyd"
File "win32ui.pyd"
File "win32wnet.pyd"
File "_ctypes.pyd"
File "_hashlib.pyd"
File "_socket.pyd"
File "_sqlite3.pyd"
File "_ssl.pyd"
File "ssleay32.dll"
File "libeay32.dll"
File "libgcc_s_dw2-1.dll"
File "matplotlib*"
File "numpy*"
File "pandas*"

SetOutPath "$INSTDIR\docs"
File "docs\"
CreateDirectory "$INSTDIR\docs"

SetOutPath "$INSTDIR\ssl"
File "ssl\"
CreateDirectory "$INSTDIR\ssl"

SetOutPath "$INSTDIR\imageformats"
File "imageformats\"
CreateDirectory "$INSTDIR\imageformats"       

SetOutPath "$INSTDIR\mpl-data"
File "mpl-data\"
CreateDirectory "$INSTDIR\mpl-data"

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

;覧覧覧覧覧・
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
