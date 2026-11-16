# Optimizador de Rendimiento GPU RTX 4050 - MSI Thin 15
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  DESBLOQUEANDO MAXIMO RENDIMIENTO RTX 4050 EN MSI THIN 15" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. Configurar Plan de Maximo Rendimiento en Windows
Write-Host "`n[1/4] Configurando Plan de Alto Rendimiento en Windows..." -ForegroundColor Green
try {
    powercfg -duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
    powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
    powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100 2>$null
    powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100 2>$null
    powercfg /change monitor-timeout-ac 0 2>$null
    powercfg /change monitor-timeout-dc 0 2>$null
    powercfg /change standby-timeout-ac 0 2>$null
    powercfg /change standby-timeout-dc 0 2>$null
    powercfg /change hibernate-timeout-ac 0 2>$null
    powercfg /change hibernate-timeout-dc 0 2>$null
    powercfg /setactive SCHEME_CURRENT 2>$null
    Write-Host "  OK: Plan de energia al 100% en CPU y PCIe (Suspension y apagado de pantalla desactivados)." -ForegroundColor Gray
} catch {
    Write-Host "  Aviso al configurar plan de energia: $_" -ForegroundColor DarkYellow
}

# 2. Desbloquear reloj de memoria VRAM (P0: 8001 MHz)
Write-Host "`n[2/4] Desbloqueando reloj de memoria VRAM a 8001 MHz..." -ForegroundColor Green
$lmcRes = nvidia-smi -lmc 8001,8001 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Reloj de VRAM bloqueado a 8001 MHz (Maximo ancho de banda GDDR6)." -ForegroundColor Gray
} else {
    $lmcSingle = nvidia-smi -lmc 8001 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  OK: Reloj de VRAM fijado a 8001 MHz." -ForegroundColor Gray
    } else {
        Write-Host "  Aviso en LMC: $lmcRes" -ForegroundColor DarkYellow
    }
}

# 3. Desbloquear reloj de nucleos CUDA
Write-Host "`n[3/4] Desbloqueando reloj de nucleos CUDA (GPU Boost)..." -ForegroundColor Green
$lgcRes = nvidia-smi -lgc 1455,2400 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK: Reloj de nucleos CUDA fijado en 1455 - 2400 MHz." -ForegroundColor Gray
} else {
    Write-Host "  Aviso: $lgcRes (Sera administrado dinamicamente por Dynamic Boost)." -ForegroundColor DarkYellow
}

# 4. Configurar PowerMizer de NVIDIA en Registro
Write-Host "`n[4/4] Configurando NVIDIA PowerMizer a Nivel 1 (Max Performance AC)..." -ForegroundColor Green
$regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0001"
try {
    if (Test-Path $regPath) {
        Set-ItemProperty -Path $regPath -Name "PowerMizerEnable" -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $regPath -Name "PowerMizerLevel" -Value 1 -Type DWord -Force
        Set-ItemProperty -Path $regPath -Name "PowerMizerLevelAC" -Value 1 -Type DWord -Force
        Write-Host "  OK: PowerMizer fijado a Nivel 1 en Registro." -ForegroundColor Gray
    }
} catch {
    Write-Host "  Aviso en Registro: $_" -ForegroundColor DarkYellow
}

Write-Host "`n======================================================================" -ForegroundColor Cyan
Write-Host "  ESTADO ACTUALIZADO DE LA GPU:" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
nvidia-smi --query-gpu=name,pstate,clocks.current.graphics,clocks.current.memory,power.draw,temperature.gpu --format=csv
Write-Host "======================================================================`n" -ForegroundColor Cyan

