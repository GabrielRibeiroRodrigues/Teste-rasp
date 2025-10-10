@echo off
REM ====================================================================
REM Teste rápido do sistema webhook
REM ====================================================================

echo.
echo ====================================================================
echo              TESTE RÁPIDO DO WEBHOOK SYSTEM
echo ====================================================================
echo.

cd /d "C:\Users\projeto\GuaritaIdentificador09-07"

echo [TESTE 1] Verificando se webhook server está rodando...
netstat -an | findstr :8080
if errorlevel 1 (
    echo ❌ Webhook server NÃO está rodando na porta 8080
    echo    Execute: start_webhook_publico.bat
    goto :end
) else (
    echo ✅ Porta 8080 está sendo usada
)

echo.
echo [TESTE 2] Testando localhost:8080/status...
powershell -Command "try { $r = Invoke-RestMethod -Uri 'http://localhost:8080/status' -TimeoutSec 5; Write-Host '✅ Webhook respondendo:' $r.status } catch { Write-Host '❌ Webhook não responde:' $_.Exception.Message }"

echo.
echo [TESTE 3] Testando ngrok URL/status...
powershell -Command "try { $r = Invoke-RestMethod -Uri 'https://spirochaetotic-yuriko-quadruply.ngrok-free.dev/status' -TimeoutSec 10; Write-Host '✅ Ngrok respondendo:' $r.status } catch { Write-Host '❌ Ngrok não responde:' $_.Exception.Message }"

echo.
echo [TESTE 4] Testando restart endpoint com token...
powershell -Command "try { $headers = @{'Authorization'='Bearer OkFbaaWhQ6w4F3Fxqf3cd-97qqOa9bHTh_Sx8Fpg8nQ'; 'Content-Type'='application/json'}; $body = '{\"test\": true}'; $r = Invoke-RestMethod -Uri 'https://spirochaetotic-yuriko-quadruply.ngrok-free.dev/restart' -Method POST -Headers $headers -Body $body -TimeoutSec 10; Write-Host '✅ Restart endpoint funcionando:' $r.status } catch { Write-Host '❌ Restart falhou:' $_.Exception.Message }"

:end
echo.
echo ====================================================================
pause
