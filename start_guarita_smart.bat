@echo off
REM ====================================================================
REM Script INTELIGENTE para iniciar o GuaritaIdentificador
REM Versao com verificacoes e restart automatico via webhook
REM ====================================================================

echo [GUARITA] Iniciando sistema inteligente...
echo Data/Hora: %date% %time%

REM Muda para o diretorio do projeto
cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

REM Verifica se o ambiente virtual existe
if not exist "env-ident\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado em: env-ident\Scripts\activate.bat
    pause
    exit /b 1
)

REM Verifica se o main.py existe
if not exist "main.py" (
    echo [ERRO] Arquivo main.py nao encontrado
    pause
    exit /b 1
)

echo [GUARITA] Ativando ambiente virtual...
call "env-ident\Scripts\activate.bat"

echo [GUARITA] Iniciando deteccao de placas...
python main.py

REM Se chegou aqui, o script terminou
echo [GUARITA] Sistema finalizado em: %date% %time%

REM Pausa apenas se houver erro
if errorlevel 1 (
    echo [ERRO] Sistema terminou com erro: %errorlevel%
    pause
)