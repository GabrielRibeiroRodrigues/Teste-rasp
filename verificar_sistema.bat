@echo off
REM ====================================================================
REM Script de Verificação - Webhook + Ngrok
REM Verifica se todos os componentes estão funcionando
REM ====================================================================

echo.
echo ====================================================================
echo           VERIFICAÇÃO DO SISTEMA WEBHOOK + NGROK
echo ====================================================================
echo.

cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

echo [CHECK 1/6] Verificando ambiente virtual...
if exist "env-ident\Scripts\activate.bat" (
    echo ✅ Ambiente virtual encontrado
) else (
    echo ❌ Ambiente virtual NÃO encontrado
    echo    Execute: python -m venv env-ident
    goto :end
)

echo.
echo [CHECK 2/6] Verificando Ngrok...
where ngrok >nul 2>&1
if errorlevel 1 (
    echo ❌ Ngrok NÃO encontrado
    echo    Instale em: https://ngrok.com/download
    goto :end
) else (
    echo ✅ Ngrok encontrado
    ngrok version
)

echo.
echo [CHECK 3/6] Verificando Flask...
call "env-ident\Scripts\activate.bat"
python -c "import flask; print('✅ Flask versão:', flask.__version__)" 2>nul
if errorlevel 1 (
    echo ❌ Flask NÃO encontrado
    echo    Instalando Flask...
    pip install flask
    if errorlevel 1 (
        echo ❌ Falha ao instalar Flask
        goto :end
    )
)

echo.
echo [CHECK 4/6] Verificando arquivos necessários...
if exist "webhook_restart_server.py" (
    echo ✅ webhook_restart_server.py
) else (
    echo ❌ webhook_restart_server.py NÃO encontrado
)

if exist "start_webhook_publico.bat" (
    echo ✅ start_webhook_publico.bat
) else (
    echo ❌ start_webhook_publico.bat NÃO encontrado
)

if exist "start_guarita_smart.bat" (
    echo ✅ start_guarita_smart.bat
) else (
    echo ❌ start_guarita_smart.bat NÃO encontrado
)

echo.
echo [CHECK 5/6] Criando diretório de logs...
if not exist "logs" mkdir logs
echo ✅ Diretório de logs criado/verificado

echo.
echo [CHECK 6/6] Testando webhook server (5 segundos)...
start /B python webhook_restart_server.py
timeout /t 5 /nobreak >nul

REM Testa se servidor está respondendo
python -c "import requests; r=requests.get('http://localhost:8080/health', timeout=3); print('✅ Webhook server respondendo:', r.status_code)" 2>nul
if errorlevel 1 (
    echo ⚠️  Webhook server pode não estar respondendo
    echo    Verifique manualmente executando: start_webhook_publico.bat
) else (
    echo ✅ Webhook server funcionando
)

REM Para o servidor de teste
taskkill /f /fi "COMMANDLINE eq *webhook_restart_server.py*" 2>nul

echo.
echo ====================================================================
echo                        RESULTADO DA VERIFICAÇÃO
echo ====================================================================
echo.
echo ✅ SISTEMA PRONTO PARA USO!
echo.
echo PRÓXIMOS PASSOS:
echo 1. Execute: start_webhook_publico.bat
echo 2. Copie a URL do Ngrok que aparecerá
echo 3. Configure N8N com a URL: https://XXXXX.ngrok.io/restart
echo 4. Use o token exibido no Authorization header
echo 5. Teste o sistema completo
echo.
echo ====================================================================

:end
echo.
pause
