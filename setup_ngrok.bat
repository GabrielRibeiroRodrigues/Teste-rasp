@echo off
REM ====================================================================
REM Setup com Ngrok para exposição do webhook na internet
REM Permite que N8N (nuvem) acesse o sistema local
REM ====================================================================

echo.
echo ====================================================================
echo        SETUP NGROK - WEBHOOK PÚBLICO PARA N8N
echo ====================================================================
echo.

REM Verifica se ngrok está instalado
where ngrok >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERRO: Ngrok não encontrado!
    echo.
    echo INSTALE O NGROK:
    echo 1. Acesse: https://ngrok.com/download
    echo 2. Baixe o executável para Windows
    echo 3. Extraia para uma pasta no PATH
    echo 4. Crie conta gratuita em: https://ngrok.com
    echo 5. Execute: ngrok authtoken SEU_TOKEN
    echo.
    pause
    exit /b 1
)

echo [STEP 1/3] Ngrok encontrado!
ngrok version

echo.
echo [STEP 2/3] Iniciando túnel público na porta 8080...
echo.
echo ====================================================================
echo IMPORTANTE: 
echo 1. Copie a URL pública que aparecerá (ex: https://abc123.ngrok.io)
echo 2. Use essa URL no N8N: https://abc123.ngrok.io/restart
echo 3. Mantenha esta janela aberta enquanto usar o sistema
echo ====================================================================
echo.

echo Pressione qualquer tecla para iniciar o túnel...
pause >nul

echo [STEP 3/3] Criando túnel público...
echo.

REM Inicia ngrok na porta 8081
ngrok http 8081
