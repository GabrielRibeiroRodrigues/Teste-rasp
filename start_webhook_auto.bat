@echo off
REM ====================================================================
REM Iniciador com detecção automática de porta livre
REM ====================================================================

echo.
echo ====================================================================
echo        WEBHOOK + NGROK - DETECÇÃO AUTOMÁTICA DE PORTA
echo ====================================================================
echo.

cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

REM Ativa ambiente virtual
call "env-ident\Scripts\activate.bat"

echo [PASSO 1] Testando portas disponíveis...

REM Testa porta 8081
netstat -an | findstr :8081 >nul
if errorlevel 1 (
    set PORTA=8081
    echo ✅ Porta 8081 está livre
    goto :start_server
)

REM Testa porta 8082
netstat -an | findstr :8082 >nul
if errorlevel 1 (
    set PORTA=8082
    echo ✅ Porta 8082 está livre
    goto :start_server
)

REM Testa porta 8083
netstat -an | findstr :8083 >nul
if errorlevel 1 (
    set PORTA=8083
    echo ✅ Porta 8083 está livre
    goto :start_server
)

echo ❌ Nenhuma porta disponível entre 8081-8083
pause
exit /b 1

:start_server
echo.
echo [PASSO 2] Iniciando webhook server na porta %PORTA%...

REM Modifica o arquivo Python temporariamente para usar a porta encontrada
powershell -Command "(Get-Content webhook_restart_server.py) -replace 'WEBHOOK_PORT = \d+', 'WEBHOOK_PORT = %PORTA%' | Set-Content webhook_restart_server_temp.py"

REM Inicia servidor em background
start /B python webhook_restart_server_temp.py

echo Aguardando servidor inicializar...
timeout /t 3 /nobreak >nul

echo.
echo [PASSO 3] Iniciando ngrok na porta %PORTA%...
echo.
echo ====================================================================
echo CONFIGURAÇÃO PARA N8N:
echo URL: https://XXXXX.ngrok.io/restart (copie da saída do ngrok)
echo Header: Authorization: Bearer OkFbaaWhQ6w4F3Fxqf3cd-97qqOa9bHTh_Sx8Fpg8nQ
echo ====================================================================
echo.

REM Inicia ngrok
ngrok http %PORTA%
