; JAI SW-8000Q Capture - NSIS Installer Script
; Requires NSIS 3.x

;--------------------------------
; Includes

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"

;--------------------------------
; General

Name "JAI SW-8000Q Capture"
OutFile "JAI_SW8000Q_Capture_Setup.exe"
InstallDir "$PROGRAMFILES64\JAI SW-8000Q Capture"
InstallDirRegKey HKLM "Software\JAI SW-8000Q Capture" "InstallDir"
RequestExecutionLevel admin
Unicode True

; Version Info
VIProductVersion "1.0.0.0"
VIAddVersionKey "ProductName" "JAI SW-8000Q Capture"
VIAddVersionKey "CompanyName" "Photometric Stereo"
VIAddVersionKey "FileDescription" "JAI SW-8000Q 4-CMOS Camera Capture Software"
VIAddVersionKey "FileVersion" "1.0.0"
VIAddVersionKey "ProductVersion" "1.0.0"
VIAddVersionKey "LegalCopyright" "Copyright (c) 2024"

;--------------------------------
; Variables

Var SDK_INSTALLED
Var SDK_INSTALLER_PATH

;--------------------------------
; Interface Settings

!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${NSISDIR}\Contrib\Graphics\Wizard\win.bmp"

;--------------------------------
; Pages

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "README.md"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;--------------------------------
; Languages

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"

;--------------------------------
; Functions

Function .onInit
    ; Check if running on 64-bit Windows
    ${IfNot} ${RunningX64}
        MessageBox MB_OK|MB_ICONSTOP "This application requires 64-bit Windows."
        Abort
    ${EndIf}

    ; Set 64-bit registry view
    SetRegView 64
FunctionEnd

Function CheckeBUSSDK
    ; Check if eBUS SDK is installed by looking for PUREGEV_ROOT environment variable
    ReadEnvStr $0 "PUREGEV_ROOT"

    ${If} $0 != ""
        ; SDK is installed
        StrCpy $SDK_INSTALLED "1"
        DetailPrint "eBUS SDK detected at: $0"
    ${Else}
        ; Also check registry as backup
        ReadRegStr $0 HKLM "SYSTEM\CurrentControlSet\Control\Session Manager\Environment" "PUREGEV_ROOT"
        ${If} $0 != ""
            StrCpy $SDK_INSTALLED "1"
            DetailPrint "eBUS SDK detected at: $0"
        ${Else}
            StrCpy $SDK_INSTALLED "0"
            DetailPrint "eBUS SDK not detected"
        ${EndIf}
    ${EndIf}
FunctionEnd

;--------------------------------
; Installer Sections

Section "eBUS SDK for JAI" SecSDK
    SectionIn RO  ; Read-only, always installed if needed

    Call CheckeBUSSDK

    ${If} $SDK_INSTALLED == "0"
        ; SDK not installed, need to install it first
        MessageBox MB_YESNO|MB_ICONQUESTION \
            "eBUS SDK for JAI is required but not installed.$\n$\n\
            The installer will now launch the eBUS SDK installer.$\n\
            Please complete the SDK installation before continuing.$\n$\n\
            Do you want to install eBUS SDK now?" \
            IDYES install_sdk IDNO skip_sdk

        install_sdk:
            ; Extract SDK installer to temp folder
            SetOutPath "$TEMP"
            File "dependencies\eBUS SDK 64-bit for JAI.6.5.3.7155.exe"
            StrCpy $SDK_INSTALLER_PATH "$TEMP\eBUS SDK 64-bit for JAI.6.5.3.7155.exe"

            DetailPrint "Launching eBUS SDK installer..."

            ; Run SDK installer and wait for it to complete
            ExecWait '"$SDK_INSTALLER_PATH"' $0

            ; Clean up
            Delete "$SDK_INSTALLER_PATH"

            ; Verify installation
            Call CheckeBUSSDK
            ${If} $SDK_INSTALLED == "0"
                MessageBox MB_OK|MB_ICONEXCLAMATION \
                    "eBUS SDK installation may not have completed successfully.$\n\
                    Please ensure the SDK is properly installed before running the application."
            ${Else}
                DetailPrint "eBUS SDK installed successfully"
            ${EndIf}

            Goto done_sdk

        skip_sdk:
            MessageBox MB_OK|MB_ICONEXCLAMATION \
                "eBUS SDK is required for this application to function.$\n\
                The application may not work correctly without it.$\n$\n\
                You can install the SDK later from the dependencies folder."

        done_sdk:
    ${Else}
        DetailPrint "eBUS SDK is already installed, skipping..."
    ${EndIf}
SectionEnd

Section "JAI SW-8000Q Capture" SecMain
    SectionIn RO  ; Required section

    SetOutPath "$INSTDIR"

    ; Install all files from main.dist
    File /r "main.dist\*.*"

    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

    ; Write registry keys
    WriteRegStr HKLM "Software\JAI SW-8000Q Capture" "InstallDir" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "DisplayName" "JAI SW-8000Q Capture"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "DisplayIcon" "$INSTDIR\main.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "Publisher" "Photometric Stereo"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "DisplayVersion" "1.0.0"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture" \
        "NoRepair" 1

    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\JAI SW-8000Q Capture"
    CreateShortcut "$SMPROGRAMS\JAI SW-8000Q Capture\JAI SW-8000Q Capture.lnk" "$INSTDIR\main.exe"
    CreateShortcut "$SMPROGRAMS\JAI SW-8000Q Capture\Uninstall.lnk" "$INSTDIR\Uninstall.exe"

    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\JAI SW-8000Q Capture.lnk" "$INSTDIR\main.exe"

SectionEnd

;--------------------------------
; Section Descriptions

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecSDK} "eBUS SDK for JAI (required for camera communication)"
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} "JAI SW-8000Q Capture application files"
!insertmacro MUI_FUNCTION_DESCRIPTION_END

;--------------------------------
; Uninstaller Section

Section "Uninstall"
    SetRegView 64

    ; Remove files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu shortcuts
    RMDir /r "$SMPROGRAMS\JAI SW-8000Q Capture"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\JAI SW-8000Q Capture.lnk"

    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\JAI SW-8000Q Capture"
    DeleteRegKey HKLM "Software\JAI SW-8000Q Capture"

SectionEnd
