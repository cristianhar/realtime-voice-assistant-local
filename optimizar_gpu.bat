@echo off
setlocal
echo ======================================================================
echo   DESBLOQUEANDO MAXIMO RENDIMIENTO RTX 4050 EN MSI THIN 15
echo ======================================================================
echo.

echo [1/4] Activando Plan de Maximo Rendimiento en Windows...
powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >nul 2>&1
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100 >nul 2>&1
powercfg /setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100 >nul 2>&1
powercfg /change monitor-timeout-ac 0 >nul 2>&1
powercfg /change monitor-timeout-dc 0 >nul 2>&1
powercfg /change standby-timeout-ac 0 >nul 2>&1
powercfg /change standby-timeout-dc 0 >nul 2>&1
powercfg /change hibernate-timeout-ac 0 >nul 2>&1
powercfg /change hibernate-timeout-dc 0 >nul 2>&1
powercfg /setactive SCHEME_CURRENT >nul 2>&1
echo   Plan de energia configurado (Suspension y apagado de pantalla desactivados).

echo.
echo [2/4] Desbloqueando reloj de memoria VRAM (P0: 8001 MHz)...
nvidia-smi -lmc 8001,8001
if %errorlevel% neq 0 (
    nvidia-smi -lmc 8001 >nul 2>&1
)

echo.
echo [3/4] Desbloqueando reloj de procesador grafico (GPU Boost CUDA)...
nvidia-smi -lgc 1455,2400

echo.
echo [4/4] Configurando perfil NVIDIA PowerMizer en Registro...
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0001" /v PowerMizerEnable /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0001" /v PowerMizerLevel /t REG_DWORD /d 1 /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0001" /v PowerMizerLevelAC /t REG_DWORD /d 1 /f >nul 2>&1

echo.
echo [5/5] Habilitando puerto 8000 en Firewall de Windows para conexion movil...
netsh advfirewall firewall add rule name="VoiceAssistantLocal" dir=in action=allow protocol=TCP localport=8000 >nul 2>&1
echo   Puerto 8000 autorizado para acceso desde el celular en tu red Wi-Fi.

echo.
echo ======================================================================
echo   ESTADO ACTUALIZADO DE LA GPU:
echo ======================================================================
nvidia-smi --query-gpu=name,pstate,clocks.current.graphics,clocks.current.memory,power.draw,temperature.gpu --format=csv
echo ======================================================================
echo.
pause
