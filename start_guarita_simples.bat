@echo off
REM ====================================================================
REM Script SIMPLES para iniciar o GuaritaIdentificador
REM Versao minimalista - execucao direta
REM ====================================================================

REM Muda para o diretorio do projeto
cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

REM Ativa ambiente e executa
call "env-ident\Scripts\activate.bat" && python main.py

REM Pausa apenas se houver erro
if errorlevel 1 pause
