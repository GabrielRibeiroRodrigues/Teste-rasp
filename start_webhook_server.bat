@echo off
REM ====================================================================
REM Script para iniciar o Webhook Server de Restart Automático
REM ====================================================================

echo.
echo ====================================================================
echo           WEBHOOK SERVER - RESTART AUTOMÁTICO GUARITA
echo ====================================================================
echo.

REM Muda para o diretório do projeto
cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

REM Verifica se o ambiente virtual existe
if not exist "env-ident\Scripts\activate.bat" (
    echo.
    echo ERRO: Ambiente virtual nao encontrado!
    echo Execute primeiro: python -m venv env-ident
    echo.
    pause
    exit /b 1
)

echo [%date% %time%] Ativando ambiente virtual...
call "env-ident\Scripts\activate.bat"

echo [%date% %time%] Instalando dependencias do webhook (se necessário)...
pip install flask --quiet

echo.
echo [%date% %time%] Iniciando Webhook Server...
echo.
echo ====================================================================
echo Servidor rodando na porta 8080
echo Para parar, pressione Ctrl+C
echo ====================================================================
echo.

REM Executa o servidor webhook
python webhook_restart_server.py

echo.
echo ====================================================================
echo [%date% %time%] Webhook Server finalizado.
echo ====================================================================
echo.
pause
