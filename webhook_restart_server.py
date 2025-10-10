#!/usr/bin/env python3
"""
Webhook Server para Restart Automático do Sistema Guarita
Recebe comandos do N8N para reinicializar o sistema quando detecta falha
"""

import json
import os
import subprocess
import time
import secrets
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import threading

# === CONFIGURAÇÕES ===
WEBHOOK_PORT = 8081  # Mudado de 8080 para 8081 (evita conflitos)
WEBHOOK_HOST = '127.0.0.1'  # Apenas localhost (mais seguro)
CONFIG_FILE = "config_webhook.json"
LOG_FILE = "logs/webhook_restart.log"

# Paths do projeto
PROJECT_DIR = Path(__file__).parent.absolute()
START_SCRIPT = PROJECT_DIR / "start_guarita_smart.bat"

# Rate limiting - máximo 1 restart a cada 5 minutos
RATE_LIMIT_SECONDS = 300  # 5 minutos
last_restart_time = 0

app = Flask(__name__)

# === FUNÇÕES UTILITÁRIAS ===
def load_config():
    """Carrega ou cria configuração com token de segurança"""
    config_path = PROJECT_DIR / CONFIG_FILE
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        # Gera token seguro automaticamente
        config = {
            "webhook_token": secrets.token_urlsafe(32),
            "created_at": datetime.now().isoformat(),
            "max_restarts_per_hour": 5,
            "rate_limit_seconds": RATE_LIMIT_SECONDS
        }
        
        # Salva configuração
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Token gerado e salvo em: {config_path}")
        print(f"🔑 Token: {config['webhook_token']}")
    
    return config

def log_event(message, level="INFO"):
    """Registra eventos no arquivo de log"""
    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    try:
        with open(log_dir / "webhook_restart.log", 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Erro ao escrever log: {e}")
    
    # Também imprime no console
    print(f"[WEBHOOK] {log_entry.strip()}")

def kill_guarita_processes():
    """Para todos os processos relacionados ao sistema guarita de forma mais agressiva"""
    killed_processes = 0
    
    # Método 1: Usar wmic para encontrar processos específicos
    wmic_commands = [
        'wmic process where "commandline like \'%main.py%\'" delete',
        'wmic process where "commandline like \'%GuaritaIdentificador%\'" delete',
        'wmic process where "commandline like \'%guarita%\'" delete'
    ]
    
    for cmd in wmic_commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
            if "deleted successfully" in result.stdout.lower():
                killed_processes += 1
                log_event(f"Processos eliminados via wmic: {result.stdout.strip()}")
        except Exception as e:
            log_event(f"Erro com wmic: {e}", "WARNING")
    
    # Método 2: Taskkill tradicional (backup)
    taskkill_commands = [
        'taskkill /f /fi "WINDOWTITLE eq *main.py*" 2>nul',
        'taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *main.py*" 2>nul',
        'taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *guarita*" 2>nul',
        'taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *GuaritaIdentificador*" 2>nul'
    ]
    
    for cmd in taskkill_commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                killed_processes += 1
        except subprocess.TimeoutExpired:
            log_event("Timeout ao tentar parar processos", "WARNING")
        except Exception as e:
            log_event(f"Erro ao parar processos: {e}", "ERROR")
    
    # Método 3: Força eliminação por PID específico se necessário
    try:
        # Busca processos Python com alta utilização de memória (indicativo de main.py)
        ps_result = subprocess.run(
            'powershell "Get-Process python* | Where-Object {$_.WorkingSet -gt 100MB} | Select-Object Id"',
            shell=True, capture_output=True, text=True, timeout=10
        )
        if ps_result.returncode == 0:
            lines = ps_result.stdout.strip().split('\n')
            for line in lines[2:]:  # Skip header lines
                try:
                    pid = int(line.strip())
                    subprocess.run(f'taskkill /f /pid {pid}', shell=True, timeout=5)
                    killed_processes += 1
                    log_event(f"Processo de alta memória eliminado: PID {pid}")
                except (ValueError, subprocess.TimeoutExpired):
                    continue
    except Exception as e:
        log_event(f"Erro ao eliminar processos de alta memória: {e}", "WARNING")
    
    return killed_processes

def start_guarita_system():
    """Inicia o sistema guarita usando o script inteligente"""
    try:
        if not START_SCRIPT.exists():
            raise FileNotFoundError(f"Script não encontrado: {START_SCRIPT}")
        
        # Executa o script em background
        process = subprocess.Popen(
            [str(START_SCRIPT)],
            cwd=str(PROJECT_DIR),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        log_event(f"Sistema iniciado com PID: {process.pid}")
        return True, process.pid
        
    except Exception as e:
        log_event(f"Erro ao iniciar sistema: {e}", "ERROR")
        return False, None

def restart_system_async():
    """Executa o restart em thread separada para não bloquear o webhook"""
    def restart_worker():
        log_event("=== INICIANDO RESTART AUTOMÁTICO ===")
        
        # Passo 1: Para processos existentes
        log_event("Parando processos do sistema guarita...")
        killed = kill_guarita_processes()
        log_event(f"Processos finalizados: {killed}")
        
        # Passo 2: Aguarda finalização completa
        time.sleep(5)
        
        # Passo 3: Inicia novo sistema
        log_event("Iniciando novo sistema...")
        success, pid = start_guarita_system()
        
        if success:
            log_event(f"✅ RESTART CONCLUÍDO COM SUCESSO - PID: {pid}")
        else:
            log_event("❌ FALHA NO RESTART", "ERROR")
        
        log_event("=== RESTART AUTOMÁTICO FINALIZADO ===")
    
    # Executa em thread separada
    thread = threading.Thread(target=restart_worker, daemon=True)
    thread.start()

# === ROTAS DO WEBHOOK ===
@app.route('/restart', methods=['POST'])
def webhook_restart():
    """Endpoint para restart automático via N8N"""
    global last_restart_time
    
    try:
        # Validação do token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            log_event("Tentativa de acesso sem token válido", "WARNING")
            return jsonify({"error": "Token de autorização obrigatório"}), 401
        
        token = auth_header.replace('Bearer ', '')
        if token != config['webhook_token']:
            log_event(f"Token inválido recebido: {token[:8]}...", "WARNING")
            return jsonify({"error": "Token inválido"}), 401
        
        # Rate limiting
        current_time = time.time()
        if current_time - last_restart_time < RATE_LIMIT_SECONDS:
            remaining = RATE_LIMIT_SECONDS - (current_time - last_restart_time)
            log_event(f"Rate limit ativo. Aguarde {remaining:.0f}s", "WARNING")
            return jsonify({
                "error": "Rate limit ativo",
                "retry_after_seconds": int(remaining)
            }), 429
        
        # Registra informações da requisição
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        log_event(f"Comando de restart recebido de {client_ip}")
        
        # Executa restart
        last_restart_time = current_time
        restart_system_async()
        
        return jsonify({
            "status": "success",
            "message": "Restart iniciado com sucesso",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        log_event(f"Erro no webhook restart: {e}", "ERROR")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route('/status', methods=['GET'])  
def webhook_status():
    """Endpoint para verificar status do webhook"""
    return jsonify({
        "status": "online",
        "service": "GuaritaIdentificador Webhook",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "project_dir": str(PROJECT_DIR),
        "start_script_exists": START_SCRIPT.exists()
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check simples para monitoramento"""
    return jsonify({"status": "healthy"}), 200

# === INICIALIZAÇÃO ===
if __name__ == '__main__':
    print("🚀 Iniciando Webhook Server para Restart Automático...")
    
    # Carrega configuração
    config = load_config()
    
    # Cria diretório de logs
    (PROJECT_DIR / "logs").mkdir(exist_ok=True)
    
    # Log de inicialização
    log_event("=== WEBHOOK SERVER INICIADO ===")
    log_event(f"Porta: {WEBHOOK_PORT}")
    log_event(f"Token: {config['webhook_token'][:8]}...")
    log_event(f"Script de start: {START_SCRIPT}")
    log_event(f"Rate limit: {RATE_LIMIT_SECONDS}s")
    
    print(f"")
    print(f"📋 CONFIGURAÇÃO PARA N8N:")
    print(f"   URL: http://localhost:{WEBHOOK_PORT}/restart")
    print(f"   Método: POST")
    print(f"   Header: Authorization: Bearer {config['webhook_token']}")
    print(f"")
    print(f"🔍 Endpoints disponíveis:")
    print(f"   POST /restart  - Executa restart do sistema")
    print(f"   GET  /status   - Status do webhook")
    print(f"   GET  /health   - Health check")
    print(f"")
    
    try:
        # Inicia servidor Flask
        app.run(
            host=WEBHOOK_HOST,
            port=WEBHOOK_PORT,
            debug=False,
            threaded=True
        )
    except Exception as e:
        log_event(f"Erro ao iniciar servidor: {e}", "ERROR")
        print(f"❌ Falha ao iniciar servidor na porta {WEBHOOK_PORT}")
        print(f"   Verifique se a porta está disponível")
