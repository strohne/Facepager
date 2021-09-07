; Start

Name "Facepager"
CRCCheck On

;General

OutFile "Facepager_Setup.exe"
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

InstallDir "$PROGRAMFILES64\Facepager"

;覧覧覧覧覧・
;Data

;覧覧覧覧覧・
;Uninstall Previous Section
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

File /r "Facepager\*"

;create desktop shortcut
CreateShortCut "$DESKTOP\Facepager.lnk" "$INSTDIR\Facepager.exe" ""

;create start-menu items
CreateDirectory "$SMPROGRAMS\Facepager"
CreateShortCut "$SMPROGRAMS\Facepager\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0
CreateShortCut "$SMPROGRAMS\Facepager\Facepager.lnk" "$INSTDIR\Facepager.exe" "" "$INSTDIR\Facepager.exe" 0

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
