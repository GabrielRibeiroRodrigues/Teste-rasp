@echo off
REM ====================================================================
REM Iniciador Completo - Webhook + Ngrok para N8N
REM Inicia tanto o webhook server quanto o túnel público
REM ====================================================================

echo.
echo ====================================================================
echo     INICIADOR COMPLETO - WEBHOOK PÚBLICO PARA N8N
echo ====================================================================
echo.

cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

echo [PASSO 1] Verificando dependências...

REM Verifica ambiente virtual
if not exist "env-ident\Scripts\activate.bat" (
    echo ERRO: Ambiente virtual não encontrado!
    pause
    exit /b 1
)

REM Verifica ngrok
where ngrok >nul 2>&1
if errorlevel 1 (
    echo ERRO: Ngrok não instalado!
    echo Instale primeiro em: https://ngrok.com/download
    pause
    exit /b 1
)

echo [PASSO 2] Ativando ambiente virtual...
call "env-ident\Scripts\activate.bat"

echo [PASSO 3] Instalando Flask (se necessário)...
pip install flask --quiet

echo [PASSO 4] Iniciando webhook server em background...
start /B python webhook_restart_server.py

echo Aguardando webhook server inicializar...
timeout /t 5 /nobreak >nul

echo [PASSO 5] Criando túnel público com ngrok...
echo.
echo ====================================================================
echo                    SISTEMA PRONTO!
echo ====================================================================
echo.
echo ✅ Webhook Server: http://localhost:8080
echo ✅ Túnel Público: Será exibido pelo Ngrok abaixo
echo.
echo 📋 PARA CONFIGURAR N8N:
echo    1. Copie a URL que aparece como "Forwarding"
echo    2. Adicione "/restart" no final
echo    3. Exemplo: https://abc123.ngrok.io/restart
echo.
echo 🔑 TOKEN DE SEGURANÇA:
echo    Verifique no console do webhook server acima
echo    Use no header: Authorization: Bearer TOKEN
echo.
echo ⚠️  IMPORTANTE: Mantenha esta janela aberta!
echo.
echo ====================================================================

REM Inicia ngrok (fica em primeiro plano)
ngrok http 8081
