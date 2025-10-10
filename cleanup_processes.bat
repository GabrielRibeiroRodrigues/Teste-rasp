@echo off
REM ====================================================================
REM Script para limpeza completa de processos Python órfãos
REM Use este script para garantir que não há instâncias antigas rodando
REM ====================================================================

echo [CLEANUP] Iniciando limpeza de processos Python órfãos...
echo Data/Hora: %date% %time%

echo [CLEANUP] Listando processos Python ativos...
wmic process where "name='python.exe'" get processid,commandline,workingsetsize /format:csv

echo.
echo [CLEANUP] Eliminando processos relacionados ao GuaritaIdentificador...

REM Método 1: WMIC (mais preciso)
wmic process where "commandline like '%%main.py%%'" delete >nul 2>&1
if %errorlevel% equ 0 echo [OK] Processos main.py eliminados via WMIC

wmic process where "commandline like '%%GuaritaIdentificador%%'" delete >nul 2>&1
if %errorlevel% equ 0 echo [OK] Processos GuaritaIdentificador eliminados via WMIC

wmic process where "commandline like '%%guarita%%'" delete >nul 2>&1
if %errorlevel% equ 0 echo [OK] Processos guarita eliminados via WMIC

REM Método 2: TaskKill (backup)
taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *main.py*" >nul 2>&1
taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *guarita*" >nul 2>&1
taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *GuaritaIdentificador*" >nul 2>&1

echo.
echo [CLEANUP] Aguardando finalização completa...
timeout /t 3 /nobreak >nul

echo [CLEANUP] Verificando processos restantes...
wmic process where "name='python.exe' and (commandline like '%%main.py%%' or commandline like '%%guarita%%')" get processid,commandline /format:csv

echo.
echo [CLEANUP] Limpeza concluída!
echo Data/Hora: %date% %time%
pause
