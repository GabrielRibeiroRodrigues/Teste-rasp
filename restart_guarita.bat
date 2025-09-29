@echo off
REM Script para reiniciar o GuaritaIdentificador via Task Scheduler
REM Executado automaticamente às 3h da madrugada

echo [%date% %time%] Iniciando reinicializacao programada do GuaritaIdentificador...

REM Para processos Python relacionados ao GuaritaIdentificador
echo [%date% %time%] Parando processos existentes...
taskkill /f /fi "WINDOWTITLE eq *main.py*" 2>nul
taskkill /f /fi "WINDOWTITLE eq *heartbeat_monitor*" 2>nul
taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *main.py*" 2>nul
taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *heartbeat_monitor*" 2>nul

REM Aguarda 5 segundos para finalização completa
echo [%date% %time%] Aguardando finalizacao completa...
timeout /t 5 /nobreak >nul

REM Limpa arquivos temporários e cache
echo [%date% %time%] Limpando cache e arquivos temporarios...
del /q "C:\Users\projeto\Monitor\status\*" 2>nul

REM Força limpeza de memória (opcional)
echo [%date% %time%] Liberando memoria do sistema...
echo. | powershell -Command "[System.GC]::Collect(); [System.GC]::WaitForPendingFinalizers()"

REM Muda para o diretório do projeto
cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

REM Ativa ambiente virtual e inicia main.py
echo [%date% %time%] Iniciando main.py com ambiente virtual...
start "GuaritaIdentificador" cmd /k "env-ident\Scripts\activate && python main.py"

REM Aguarda alguns segundos e inicia o monitor
echo [%date% %time%] Aguardando inicializacao do main.py...
timeout /t 10 /nobreak >nul

echo [%date% %time%] Iniciando heartbeat_monitor.py...
start "GuaritaMonitor" cmd /k "env-ident\Scripts\activate && python heartbeat_monitor.py"

echo [%date% %time%] Reinicializacao programada concluida com sucesso!
echo [%date% %time%] main.py e heartbeat_monitor.py iniciados em janelas separadas.

REM Log da operação
echo [%date% %time%] Restart programado executado com sucesso >> "C:\Users\projeto\GuaritaIdentificador09-07\restart_log.txt"