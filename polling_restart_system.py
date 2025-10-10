#!/usr/bin/env python3
"""
Sistema de Polling para Restart - Alternativa ao Webhook
O sistema local consulta o N8N periodicamente em busca de comandos
Não precisa de ngrok ou exposição de portas
"""

import json
import os
import subprocess
import time
import requests
from datetime import datetime
from pathlib import Path

# === CONFIGURAÇÕES ===
N8N_COMMAND_URL = "https://campusinteligente.ifsuldeminas.edu.br/n8n/webhook/WEBHOOK_COMANDO_ID"
POLLING_INTERVAL = 60  # Verifica comandos a cada 60 segundos
PROJECT_DIR = Path(__file__).parent.absolute()
START_SCRIPT = PROJECT_DIR / "start_guarita_smart.bat"
LOG_FILE = PROJECT_DIR / "logs" / "polling_restart.log"

# Rate limiting
RATE_LIMIT_SECONDS = 300  # Max 1 restart a cada 5 minutos
last_restart_time = 0

def log_event(message, level="INFO"):
    """Registra eventos no arquivo de log"""
    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Erro ao escrever log: {e}")
    
    print(f"[POLLING] {log_entry.strip()}")

def check_for_restart_command():
    """Verifica se há comando de restart no N8N"""
    try:
        response = requests.get(N8N_COMMAND_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Verifica se há comando de restart pendente
            if data.get('command') == 'restart' and data.get('executed') != True:
                log_event("Comando de restart recebido do N8N")
                return True, data.get('reason', 'no_reason')
        
        return False, None
    
    except requests.exceptions.RequestException as e:
        log_event(f"Erro ao verificar comandos no N8N: {e}", "WARNING")
        return False, None

def mark_command_as_executed():
    """Marca comando como executado no N8N"""
    try:
        payload = {
            "command": "restart",
            "executed": True,
            "executed_at": datetime.now().isoformat(),
            "status": "completed"
        }
        
        response = requests.post(N8N_COMMAND_URL, json=payload, timeout=10)
        if response.status_code == 200:
            log_event("Comando marcado como executado no N8N")
        else:
            log_event(f"Falha ao marcar comando como executado: {response.status_code}", "WARNING")
    
    except Exception as e:
        log_event(f"Erro ao marcar comando como executado: {e}", "ERROR")

def kill_guarita_processes():
    """Para todos os processos relacionados ao sistema guarita"""
    commands = [
        'taskkill /f /fi "WINDOWTITLE eq *main.py*" 2>nul',
        'taskkill /f /fi "IMAGENAME eq python.exe" /fi "COMMANDLINE eq *main.py*" 2>nul'
    ]
    
    killed_processes = 0
    for cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                killed_processes += 1
        except Exception as e:
            log_event(f"Erro ao parar processos: {e}", "ERROR")
    
    return killed_processes

def start_guarita_system():
    """Inicia o sistema guarita"""
    try:
        if not START_SCRIPT.exists():
            raise FileNotFoundError(f"Script não encontrado: {START_SCRIPT}")
        
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

def execute_restart(reason="unknown"):
    """Executa o restart do sistema"""
    global last_restart_time
    
    current_time = time.time()
    if current_time - last_restart_time < RATE_LIMIT_SECONDS:
        remaining = RATE_LIMIT_SECONDS - (current_time - last_restart_time)
        log_event(f"Rate limit ativo. Aguarde {remaining:.0f}s", "WARNING")
        return False
    
    log_event(f"=== INICIANDO RESTART AUTOMÁTICO - Motivo: {reason} ===")
    
    # Para processos existentes
    log_event("Parando processos do sistema guarita...")
    killed = kill_guarita_processes()
    log_event(f"Processos finalizados: {killed}")
    
    # Aguarda finalização
    time.sleep(5)
    
    # Inicia novo sistema
    log_event("Iniciando novo sistema...")
    success, pid = start_guarita_system()
    
    if success:
        log_event(f"✅ RESTART CONCLUÍDO COM SUCESSO - PID: {pid}")
        last_restart_time = current_time
        mark_command_as_executed()
        return True
    else:
        log_event("❌ FALHA NO RESTART", "ERROR")
        return False

def main():
    """Loop principal de polling"""
    log_event("=== SISTEMA DE POLLING INICIADO ===")
    log_event(f"Intervalo de polling: {POLLING_INTERVAL} segundos")
    log_event(f"URL de comando: {N8N_COMMAND_URL}")
    
    while True:
        try:
            # Verifica por comandos
            should_restart, reason = check_for_restart_command()
            
            if should_restart:
                success = execute_restart(reason)
                if success:
                    log_event("Restart executado com sucesso")
                else:
                    log_event("Falha no restart", "ERROR")
            
            # Aguarda próxima verificação
            time.sleep(POLLING_INTERVAL)
            
        except KeyboardInterrupt:
            log_event("Sistema de polling interrompido pelo usuário")
            break
        except Exception as e:
            log_event(f"Erro no loop principal: {e}", "ERROR")
            time.sleep(POLLING_INTERVAL)

if __name__ == '__main__':
    print("🔄 Iniciando Sistema de Polling para Restart Automático...")
    print(f"📡 Consultando N8N a cada {POLLING_INTERVAL} segundos")
    print(f"📁 Logs em: {LOG_FILE}")
    print(f"⏹️  Para parar: Ctrl+C")
    print()
    
    try:
        main()
    except Exception as e:
        log_event(f"Erro fatal: {e}", "ERROR")
        print(f"❌ Erro fatal: {e}")
