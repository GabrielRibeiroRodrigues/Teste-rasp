# Configuração N8N para Restart Automático do Sistema Guarita

## WORKFLOW N8N - Monitoramento e Restart Automático

### 1. CRON TRIGGER NODE
```json
{
  "schedule": "*/5 * * * *",
  "description": "Executa a cada 5 minutos"
}
```

### 2. HTTP REQUEST NODE - Verificar Heartbeat
```json
{
  "method": "GET",
  "url": "https://campusinteligente.ifsuldeminas.edu.br/n8n/webhook/0615ade6-36bb-46b2-813b-84ada7c61a55/status",
  "timeout": 30000,
  "description": "Verifica quando foi o último heartbeat"
}
```

### 3. SET NODE - Calcular Tempo Desde Último Heartbeat
```json
{
  "values": {
    "tempo_desde_ultimo": "={{ Math.floor((Date.now() - new Date($json.ultimo_heartbeat).getTime()) / 1000 / 60) }}",
    "status_sistema": "={{ $json.tempo_desde_ultimo > 20 ? 'falha' : 'ok' }}"
  }
}
```

### 4. IF NODE - Sistema em Falha?
```json
{
  "conditions": {
    "string": [
      {
        "value1": "={{$json.status_sistema}}",
        "operation": "equal",
        "value2": "falha"
      }
    ]
  }
}
```

### 5. HTTP REQUEST NODE - Executar Restart (Ramo TRUE)
```json
{
  "method": "POST",
  "url": "http://IP_DO_SERVIDOR:8080/restart",
  "headers": {
    "Authorization": "Bearer SEU_TOKEN_AQUI",
    "Content-Type": "application/json"
  },
  "body": {
    "source": "n8n_auto_restart",
    "reason": "heartbeat_timeout",
    "timestamp": "={{ new Date().toISOString() }}"
  },
  "timeout": 45000
}
```

### 6. WEBHOOK NODE - Notificação WhatsApp (Opcional)
```json
{
  "method": "GET",
  "url": "https://api.callmebot.com/whatsapp.php",
  "parameters": {
    "phone": "SEU_NUMERO",
    "text": "🔄 Sistema Guarita reiniciado automaticamente pelo N8N em {{ new Date().toLocaleString('pt-BR') }}",
    "apikey": "SUA_API_KEY"
  }
}
```

## OPÇÕES DE CONEXÃO N8N ↔ SISTEMA LOCAL

### OPÇÃO A: WEBHOOK COM NGROK (Recomendada)
```
Sistema Local + Ngrok → Internet → N8N (nuvem)
```

### OPÇÃO B: SISTEMA DE POLLING  
```
Sistema Local consulta N8N → N8N responde com comando
```

---

## CONFIGURAÇÃO OPÇÃO A: WEBHOOK + NGROK

### Passo 1: Instalar Ngrok
1. Acesse: https://ngrok.com/download
2. Baixe o executável para Windows
3. Crie conta gratuita
4. Execute: `ngrok authtoken SEU_TOKEN`

### Passo 2: Iniciar Sistema Completo
1. Execute: `start_webhook_publico.bat`
2. Copie a URL pública exibida (ex: `https://abc123.ngrok.io`)
3. Use essa URL no N8N: `https://abc123.ngrok.io/restart`

### Passo 3: Obter Token de Segurança
- Token será exibido no console do webhook
- Use no header: `Authorization: Bearer TOKEN`

---

## CONFIGURAÇÃO OPÇÃO B: POLLING (Sem Ngrok)

### Passo 1: Criar Webhook de Comando no N8N
1. Crie novo webhook no N8N: `/webhook/comando-restart`
2. Configure para aceitar GET e POST
3. Anote a URL do webhook

### Passo 2: Configurar Polling System
1. Edite `polling_restart_system.py`
2. Substitua `N8N_COMMAND_URL` pela URL do webhook
3. Execute: `python polling_restart_system.py`

### Passo 3: Criar Workflow no N8N
1. Acesse seu N8N
2. Crie novo workflow
3. Adicione os nodes conforme configuração acima
4. Configure as conexões entre os nodes
5. Ative o workflow

### Passo 4: Testar o Sistema
1. Inicie o webhook server: `start_webhook_server.bat`
2. Inicie o sistema guarita: `start_guarita_smart.bat`
3. Pare o sistema guarita manualmente
4. Aguarde 20+ minutos
5. Verifique se N8N reinicia automaticamente

## FLUXO COMPLETO

```
N8N (a cada 5 min) → Verifica último heartbeat
     ↓
Último heartbeat > 20 min? 
     ↓ (SIM)
POST http://servidor:8080/restart + token
     ↓
Webhook Server valida token
     ↓
Executa: taskkill + start_guarita_smart.bat
     ↓
Sistema reinicia e volta a enviar heartbeat
     ↓
N8N detecta que voltou ✅
```

## SEGURANÇA

- ✅ Token de autenticação obrigatório
- ✅ Rate limiting (máximo 1 restart por 5 minutos)
- ✅ Logs detalhados de todas as operações
- ✅ Validação de origem das requisições

## MONITORAMENTO

### Logs do Webhook:
- Arquivo: `logs/webhook_restart.log`
- Contém: timestamps, IPs, tokens, resultados

### Endpoints de Status:
- `GET /status` - Status detalhado do webhook
- `GET /health` - Health check simples

### Estatísticas:
- Número de restarts executados
- Últimos horários de restart
- Taxa de sucesso/falha
