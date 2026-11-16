# ==============================================================================
# Script para crear acceso directo en el Escritorio de Windows (Desktop Launcher)
# ==============================================================================

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path -Path $DesktopPath -ChildPath "VoiceChat AI Local.lnk"

$TargetScript = Join-Path -Path $PSScriptRoot -ChildPath "launch_voice_assistant.bat"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetScript
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "VoiceChat AI - Asistente de Voz 100% Local en Tiempo Real"

# Buscar icono en Edge, Chrome o icono de microfono de shell32
$IconPath = ""
if (Test-Path "$env:ProgramFiles (x86)\Microsoft\Edge\Application\msedge.exe") {
    $IconPath = "$env:ProgramFiles (x86)\Microsoft\Edge\Application\msedge.exe,0"
} elseif (Test-Path "$env:ProgramFiles\Google\Chrome\Application\chrome.exe") {
    $IconPath = "$env:ProgramFiles\Google\Chrome\Application\chrome.exe,0"
} else {
    $IconPath = "$env:SystemRoot\System32\shell32.dll,246"
}

try {
    $Shortcut.Save()
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host "  ✅ ACCESO DIRECTO CREADO EXITOSAMENTE EN TU ESCRITORIO" -ForegroundColor Green
    Write-Host "=====================================================================" -ForegroundColor Green
    Write-Host "Ubicacion: $ShortcutPath" -ForegroundColor Cyan
    Write-Host "Ahora puedes iniciar VoiceChat AI con doble clic en tu escritorio!" -ForegroundColor Yellow
    Write-Host "=====================================================================" -ForegroundColor Green
} catch {
    Write-Host "[!] No se pudo escribir directamente en el Escritorio desde este entorno restringido." -ForegroundColor Yellow
    Write-Host "Puedes ejecutar este script directamente en tu PowerShell de Windows:" -ForegroundColor Cyan
    Write-Host "powershell -ExecutionPolicy Bypass -File .\create_desktop_shortcut.ps1" -ForegroundColor White
}
