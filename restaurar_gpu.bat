@echo off
chcp 65001 >nul
title Restaurar Valores de Fabrica GPU - MSI Thin 15

:: Comprobar si se ejecuta como Administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo [1/3] Restaurando relojes de memoria de GPU...
nvidia-smi -rmc >nul 2>&1

echo [2/3] Restaurando relojes de nucleos de GPU...
nvidia-smi -rgc >nul 2>&1

echo [3/3] Restaurando plan de energia equilibrado...
powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e >nul 2>&1

echo.
echo ✓ GPU y planes de energia restaurados a los valores estandar de fabrica.
pause

