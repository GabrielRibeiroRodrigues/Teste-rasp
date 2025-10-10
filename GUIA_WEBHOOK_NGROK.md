# GUIA COMPLETO - SOLUÇÃO A: WEBHOOK + NGROK

## ✅ PASSO A PASSO PARA IMPLEMENTAR

### PASSO 1: INSTALAR NGROK
1. Acesse: https://ngrok.com/download
2. Baixe `ngrok.exe` para Windows
3. Coloque o arquivo em uma pasta (ex: `C:\ngrok\`)
4. Adicione a pasta ao PATH ou use caminho completo

### PASSO 2: CRIAR CONTA NGROK (GRATUITA)
1. Acesse: https://ngrok.com/signup
2. Crie conta gratuita
3. Copie seu AuthToken da dashboard
4. Execute: `ngrok authtoken SEU_TOKEN_AQUI`

### PASSO 3: INSTALAR DEPENDÊNCIAS
```bash
# Execute no seu projeto:
cd C:\Users\projeto\GuaritaIdentificador09-07
pip install flask
```

### PASSO 4: INICIAR SISTEMA COMPLETO
```bash
# Execute este comando:
start_webhook_publico.bat
```

### PASSO 5: COPIAR URLs
O script mostrará algo como:
```
====================================================================
WEBHOOK + NGROK RODANDO!

1. Webhook Server: localhost:8080 ✅
2. Túnel Público: https://abc123-def456.ngrok.io ✅

COPIE A URL PÚBLICA PARA USAR NO N8N!
Formato: https://abc123-def456.ngrok.io/restart
====================================================================

Token: AbC123DeF456GhI789... (copie este token também)
```

### PASSO 6: CONFIGURAR N8N

#### Workflow N8N:
1. **Cron Node**: `*/5 * * * *` (a cada 5 minutos)
2. **Set Node**: Calcular tempo desde último heartbeat
3. **If Node**: Se > 20 minutos sem heartbeat
4. **HTTP Request Node** (configuração abaixo):

```json
{
  "method": "POST",
  "url": "https://SUA_URL_NGROK.ngrok.io/restart",
  "headers": {
    "Authorization": "Bearer SEU_TOKEN_COPIADO",
    "Content-Type": "application/json"
  },
  "body": {
    "source": "n8n_auto_restart",
    "reason": "heartbeat_timeout_20min",
    "timestamp": "{{ $now }}"
  }
}
```

### PASSO 7: TESTAR O SISTEMA
1. Certifique-se que `start_webhook_publico.bat` está rodando
2. Inicie o sistema principal: `start_guarita_smart.bat`
3. Pare o sistema principal (Ctrl+C)
4. Aguarde 20+ minutos
5. Verifique se N8N reinicia automaticamente

---

## 🔧 COMANDOS IMPORTANTES

### Iniciar Webhook + Ngrok:
```bash
start_webhook_publico.bat
```

### Verificar Status do Webhook:
```bash
curl https://SUA_URL.ngrok.io/status
```

### Testar Restart Manual:
```bash
curl -X POST https://SUA_URL.ngrok.io/restart \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

---

## 📋 CHECKLIST DE VERIFICAÇÃO

- [ ] Ngrok instalado e autenticado
- [ ] Flask instalado (`pip install flask`)
- [ ] `start_webhook_publico.bat` executando
- [ ] URL pública do ngrok copiada
- [ ] Token de segurança copiado
- [ ] N8N configurado com URL e token
- [ ] Workflow N8N ativado
- [ ] Teste manual funcionando

---

## 🚨 TROUBLESHOOTING

### Erro: "ngrok not found"
- Instale ngrok ou adicione ao PATH
- Ou use caminho completo: `C:\caminho\para\ngrok.exe http 8080`

### Erro: "401 Unauthorized"
- Verifique se o token no N8N está correto
- Token deve ter formato: `Bearer ABC123...`

### Erro: "Connection refused"
- Verifique se webhook server está rodando na porta 8080
- Verifique se ngrok está apontando para porta 8080

### Ngrok desconecta:
- Conta gratuita tem limite de tempo
- Crie nova sessão ou considere conta paga

---

## 🔐 SEGURANÇA

✅ **Token aleatório** de 32 caracteres
✅ **Rate limiting** - máximo 1 restart por 5 minutos  
✅ **Logs detalhados** em `logs/webhook_restart.log`
✅ **Validação de origem** das requisições

---

## 📊 MONITORAMENTO

### Logs do Sistema:
- **Webhook**: `logs/webhook_restart.log`
- **Sistema**: Output do `start_guarita_smart.bat`

### Endpoints de Status:
- `GET /status` - Status detalhado
- `GET /health` - Health check simples

### Estatísticas N8N:
- Número de heartbeats recebidos
- Número de restarts executados
- Taxa de sucesso/falha
