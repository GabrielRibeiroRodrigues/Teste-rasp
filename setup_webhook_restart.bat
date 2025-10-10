@echo off
REM ====================================================================
REM Setup Automático - Sistema de Restart via N8N
REM Instala e configura tudo automaticamente
REM ====================================================================

echo.
echo ====================================================================
echo        SETUP AUTOMÁTICO - SISTEMA DE RESTART VIA N8N
echo ====================================================================
echo.

REM Muda para o diretório do projeto
cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

echo [STEP 1/5] Verificando ambiente virtual...
if not exist "env-ident\Scripts\activate.bat" (
    echo ERRO: Ambiente virtual não encontrado!
    echo Execute primeiro: python -m venv env-ident
    pause
    exit /b 1
)

echo [STEP 2/5] Ativando ambiente virtual...
call "env-ident\Scripts\activate.bat"

echo [STEP 3/5] Instalando dependências do webhook...
pip install -r requirements_webhook.txt

echo [STEP 4/5] Criando diretório de logs...
if not exist "logs" mkdir logs

echo [STEP 5/5] Testando webhook server...
echo.
echo ====================================================================
echo CONFIGURAÇÃO CONCLUÍDA!
echo.
echo PRÓXIMOS PASSOS:
echo.
echo 1. Iniciar webhook server:
echo    start_webhook_server.bat
echo.
echo 2. Copiar token exibido no console
echo.
echo 3. Configurar N8N com as instruções em:
echo    CONFIGURACAO_N8N.md
echo.
echo 4. Testar o sistema completo
echo.
echo ====================================================================
echo.

REM Inicia o servidor para mostrar o token
echo Iniciando servidor webhook para gerar token...
echo.
timeout /t 3 /nobreak >nul
python webhook_restart_server.py

pause
