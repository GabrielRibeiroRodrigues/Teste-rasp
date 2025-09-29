#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heartbeat Monitor para main.py
Monitora se o script main.py está rodando através de arquivos de status.
"""

import os
import time
import json
import psutil
import requests
import urllib.parse
import subprocess
from datetime import datetime, timedelta

# Configurações
MONITOR_DIR = "C:\\Users\\projeto\\Monitor"
STATUS_DIR = os.path.join(MONITOR_DIR, "status")
HEARTBEAT_FILE = os.path.join(STATUS_DIR, "main_heartbeat.txt")
STATUS_FILE = os.path.join(STATUS_DIR, "main_status.json")
PID_FILE = os.path.join(STATUS_DIR, "main.pid")

# Thresholds
HEARTBEAT_TIMEOUT = 1200  # Considera "sem resposta" após 20 minutos (15min + 5min tolerância)
CHECK_INTERVAL = 900      # Verifica a cada 15 minutos (mesmo intervalo do heartbeat)

# WhatsApp Configuration (CallMeBot) - Múltiplos contatos
WHATSAPP_ENABLED = True
WHATSAPP_CONTACTS = [
    {"phone": "553591872683", "api_key": "4936257", "name": "Principal"},
    {"phone": "5591177033", "api_key": "SUA_SEGUNDA_API_KEY", "name": "Secundário"}
    # Adicione mais contatos aqui se necessário
]
WHATSAPP_COOLDOWN = 1800  # Não envia mesma mensagem por 30 minutos (anti-spam)

# Auto-restart Configuration
AUTO_RESTART_ENABLED = True
AUTO_RESTART_MAX_ATTEMPTS = 3
AUTO_RESTART_DELAY = 30  # segundos entre tentativas
AUTO_RESTART_COOLDOWN = 3600  # 1 hora entre ciclos de restart
PROJECT_DIR = "C:\\Users\\projeto\\GuaritaIdentificador09-07"
ENV_NAME = "env-ident"
MAIN_SCRIPT = "main.py"

# Variáveis de controle para anti-spam e auto-restart
last_whatsapp_alerts = {}
restart_attempts = 0
last_restart_cycle = 0

def restart_main_script():
    """
    Tenta reiniciar o main.py usando ambiente virtual
    
    Returns:
        bool: True se comando foi executado com sucesso, False caso contrário
    """
    global restart_attempts, last_restart_cycle
    
    if not AUTO_RESTART_ENABLED:
        return False
    
    current_time = time.time()
    
    # Verifica cooldown do ciclo de restart
    if current_time - last_restart_cycle < AUTO_RESTART_COOLDOWN:
        print(f"{format_timestamp()} ⏳ Auto-restart em cooldown")
        return False
    
    # Verifica se atingiu limite de tentativas
    if restart_attempts >= AUTO_RESTART_MAX_ATTEMPTS:
        print(f"{format_timestamp()} ❌ Limite de restart atingido ({AUTO_RESTART_MAX_ATTEMPTS})")
        send_whatsapp_alert("Limite de restart atingido - intervenção manual necessária", "critical")
        last_restart_cycle = current_time
        restart_attempts = 0
        return False
    
    restart_attempts += 1
    
    try:
        print(f"{format_timestamp()} 🔄 Tentando restart automático ({restart_attempts}/{AUTO_RESTART_MAX_ATTEMPTS})")
        send_whatsapp_alert(f"Reiniciando main.py automaticamente ({restart_attempts}/{AUTO_RESTART_MAX_ATTEMPTS})", "info")
        
        # Comando para ativar env e executar main.py
        command = f"cd {PROJECT_DIR} && {ENV_NAME}\\Scripts\\activate && python {MAIN_SCRIPT}"
        
        # Executa comando em nova janela CMD
        process = subprocess.Popen([
            "cmd", "/c", "start", "cmd", "/k", command
        ], shell=True)
        
        print(f"{format_timestamp()} ✅ Comando de restart executado")
        
        # Aguarda delay antes da próxima verificação
        time.sleep(AUTO_RESTART_DELAY)
        
        return True
        
    except Exception as e:
        print(f"{format_timestamp()} ❌ Erro ao executar restart: {e}")
        send_whatsapp_alert(f"Erro no restart: {str(e)}", "critical")
        return False

def send_whatsapp_alert(message, alert_type="warning"):
    """
    Envia alerta via WhatsApp usando CallMeBot API para múltiplos contatos
    
    Args:
        message (str): Mensagem a ser enviada
        alert_type (str): Tipo do alerta (warning, critical, recovery, info)
    
    Returns:
        bool: True se enviado com sucesso para pelo menos um contato, False caso contrário
    """
    if not WHATSAPP_ENABLED:
        return False
    
    # Verifica se há contatos configurados
    valid_contacts = [c for c in WHATSAPP_CONTACTS if 
                     c.get("phone") != "SEU_SEGUNDO_NUMERO" and 
                     c.get("api_key") != "SUA_SEGUNDA_API_KEY"]
    
    if not valid_contacts:
        if alert_type == "critical":
            print(f"{format_timestamp()} ⚠️ Nenhum contato WhatsApp configurado")
        return False
    
    # Anti-spam: verifica se mesma mensagem foi enviada recentemente
    message_hash = hash(f"{alert_type}_{message[:50]}")
    current_time = time.time()
    
    if message_hash in last_whatsapp_alerts:
        if current_time - last_whatsapp_alerts[message_hash] < WHATSAPP_COOLDOWN:
            return False
    
    # Adiciona emoji baseado no tipo
    emoji_map = {
        "warning": "⚠️",
        "critical": "🚨", 
        "recovery": "✅",
        "info": "ℹ️"
    }
    
    emoji = emoji_map.get(alert_type, "📢")
    timestamp = datetime.now().strftime("%H:%M")
    formatted_message = f"{emoji} GuaritaID [{timestamp}]\n{message}"
    
    success_count = 0
    
    # Envia para todos os contatos válidos
    for contact in valid_contacts:
        phone = contact.get("phone")
        api_key = contact.get("api_key")
        name = contact.get("name", "Desconhecido")
        
        try:
            encoded_message = urllib.parse.quote(formatted_message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={api_key}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"{format_timestamp()} 📱 WhatsApp enviado para {name}: {alert_type}")
                success_count += 1
            elif response.status_code == 203:
                print(f"{format_timestamp()} ❌ WhatsApp ERROR 203 ({name}): Não ativado corretamente")
            elif response.status_code == 401:
                print(f"{format_timestamp()} ❌ WhatsApp ERROR 401 ({name}): API Key inválida")
            else:
                print(f"{format_timestamp()} ❌ WhatsApp ERROR {response.status_code} ({name})")
                
        except requests.exceptions.Timeout:
            print(f"{format_timestamp()} ❌ WhatsApp timeout ({name})")
        except Exception as e:
            print(f"{format_timestamp()} ❌ Erro WhatsApp ({name}): {e}")
    
    if success_count > 0:
        last_whatsapp_alerts[message_hash] = current_time
        return True
    
    return False

def test_whatsapp_config():
    """Testa a configuração do WhatsApp e fornece diagnósticos detalhados"""
    print(f"\n{format_timestamp()} 🧪 TESTE DE CONFIGURAÇÃO WHATSAPP")
    print("=" * 60)
    
    # Verifica se há contatos configurados
    valid_contacts = [c for c in WHATSAPP_CONTACTS if 
                     c.get("phone") != "SEU_SEGUNDO_NUMERO" and 
                     c.get("api_key") != "SUA_SEGUNDA_API_KEY"]
    
    if not valid_contacts:
        print("❌ ERRO: Nenhum contato configurado")
        print("💡 Configure pelo menos um contato em WHATSAPP_CONTACTS")
        return False
    
    print(f"📱 Contatos configurados: {len(valid_contacts)}")
    
    # Testa cada contato
    for i, contact in enumerate(valid_contacts, 1):
        phone = contact.get("phone", "N/A")
        api_key = contact.get("api_key", "N/A")
        name = contact.get("name", f"Contato {i}")
        
        print(f"\n--- Contato {i}: {name} ---")
        print(f"📱 Número: {phone}")
        print(f"🔑 API Key: {api_key}")
        
        # Valida formato do número
        if len(phone) < 10:
            print("❌ ERRO: Número muito curto")
            continue
        elif len(phone) > 15:
            print("❌ ERRO: Número muito longo")
            continue
        elif not phone.isdigit():
            print("❌ ERRO: Número deve conter apenas dígitos")
            continue
        else:
            print("✅ Formato do número correto")
        
        # Valida API key
        if len(api_key) < 4:
            print("❌ ERRO: API Key muito curta")
            continue
        else:
            print("✅ API Key tem tamanho adequado")
        
        print(f"🔍 Testando conexão com {name}...")
        
        try:
            test_message = f"TESTE de configuração do monitor - {name}"
            encoded_message = urllib.parse.quote(test_message)
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={api_key}"
            
            response = requests.get(url, timeout=15)
            
            print(f"📡 Resposta HTTP: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ SUCESSO! {name} configurado corretamente")
                print(f"📱 {name} deve ter recebido mensagem de teste")
            elif response.status_code == 203:
                print(f"❌ ERROR 203: {name} não ativou CallMeBot corretamente")
            elif response.status_code == 401:
                print(f"❌ ERROR 401: API Key inválida para {name}")
            else:
                print(f"❌ ERROR {response.status_code} para {name}")
                
        except Exception as e:
            print(f"❌ Erro de conexão para {name}: {e}")
    
    print(f"\n💡 CHECKLIST PARA ATIVAÇÃO:")
    print(f"1. ✅ Adicione +34 644 59 71 67 no WhatsApp")
    print(f"2. ✅ Envie EXATAMENTE: 'I allow callmebot to send me messages'")
    print(f"3. ✅ Aguarde resposta com a API key")
    print(f"4. ✅ Use a API key recebida para cada número")
    print(f"5. ✅ Configure todos os números em WHATSAPP_CONTACTS")
    
    return True

def format_timestamp():
    """Retorna timestamp formatado para logs"""
    return datetime.now().strftime("[%H:%M:%S]")

def check_process_exists(pid):
    """Verifica se um processo com o PID existe"""
    try:
        return psutil.pid_exists(int(pid))
    except (ValueError, TypeError):
        return False

def parse_heartbeat_file():
    """Lê e parseia o arquivo de heartbeat"""
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            content = f.read().strip()
        
        # Formato: "2024-01-15 14:30:22|frame_1500|placas_45|uptime_3600|running"
        parts = content.split('|')
        if len(parts) >= 5:
            timestamp_str = parts[0]
            frame_info = parts[1]
            placas_info = parts[2]
            uptime_info = parts[3]
            status = parts[4]
            
            # Parse timestamp
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            
            # Parse números
            frame_num = int(frame_info.split('_')[1]) if '_' in frame_info else 0
            placas_num = int(placas_info.split('_')[1]) if '_' in placas_info else 0
            uptime_sec = int(uptime_info.split('_')[1]) if '_' in uptime_info else 0
            
            return {
                'timestamp': timestamp,
                'frame': frame_num,
                'placas': placas_num,
                'uptime': uptime_sec,
                'status': status,
                'raw_content': content
            }
    except Exception as e:
        return {'error': str(e)}
    
    return None

def read_status_file():
    """Lê o arquivo de status JSON"""
    try:
        with open(STATUS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        return {'error': str(e)}

def read_pid_file():
    """Lê o PID do arquivo"""
    try:
        with open(PID_FILE, 'r') as f:
            return int(f.read().strip())
    except Exception:
        return None

def format_uptime(seconds):
    """Formata uptime em formato legível"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours}h{minutes:02d}m{secs:02d}s"

def monitor_main_script():
    """Função principal de monitoramento"""
    global restart_attempts
    
    print(f"{format_timestamp()} 🔍 Monitor iniciado - verificação básica a cada 15 min")
    print(f"{format_timestamp()} 🔄 Auto-restart: {'HABILITADO' if AUTO_RESTART_ENABLED else 'DESABILITADO'}")
    
    # Verifica configuração do WhatsApp
    if WHATSAPP_ENABLED:
        valid_contacts = [c for c in WHATSAPP_CONTACTS if 
                         c.get("phone") != "SEU_SEGUNDO_NUMERO" and 
                         c.get("api_key") != "SUA_SEGUNDA_API_KEY"]
        contact_names = [c.get("name", "N/A") for c in valid_contacts]
        print(f"{format_timestamp()} 📱 WhatsApp: HABILITADO ({len(valid_contacts)} contatos: {', '.join(contact_names)})")
        # Mensagem inicial simplificada
        send_whatsapp_alert("Monitor iniciado", "info")
    else:
        print(f"{format_timestamp()} 📱 WhatsApp: DESABILITADO")
    
    print("-" * 50)
    
    last_status = None
    
    while True:
        try:
            current_time = datetime.now()
            
            # Verifica apenas se arquivo de heartbeat existe
            if os.path.exists(HEARTBEAT_FILE):
                heartbeat_data = parse_heartbeat_file()
                
                if heartbeat_data and 'error' not in heartbeat_data:
                    time_diff = (current_time - heartbeat_data['timestamp']).total_seconds()
                    
                    if time_diff <= HEARTBEAT_TIMEOUT:
                        # Tudo OK - log simplificado
                        print(f"{format_timestamp()} ✅ main.py: OK")
                        
                        # Alerta de recuperação apenas se estava com problema
                        if last_status in ["problem", "stopped"]:
                            send_whatsapp_alert("main.py voltou a funcionar", "recovery")
                            restart_attempts = 0  # Reset contador de restart
                        
                        last_status = "running"
                        
                    else:
                        # Problema detectado
                        print(f"{format_timestamp()} ❌ main.py: SEM RESPOSTA há {int(time_diff/60)} min")
                        
                        if last_status != "problem":
                            send_whatsapp_alert("main.py parou de responder", "critical")
                            # Tenta restart automático
                            restart_main_script()
                        
                        last_status = "problem"
                else:
                    print(f"{format_timestamp()} ❌ main.py: ERRO DE LEITURA")
                    if last_status != "problem":
                        send_whatsapp_alert("main.py com problemas", "critical")
                        # Tenta restart automático
                        restart_main_script()
                    last_status = "problem"
            else:
                # Arquivo não existe
                print(f"{format_timestamp()} ❌ main.py: NÃO RODANDO")
                
                if last_status != "stopped":
                    send_whatsapp_alert("main.py não está rodando", "critical")
                    # Tenta restart automático
                    restart_main_script()
                
                last_status = "stopped"
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print(f"\n{format_timestamp()} 🛑 Monitor parado")
            break
        except Exception as e:
            print(f"{format_timestamp()} ❌ Erro: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Cria diretório de monitoramento se não existir
    try:
        os.makedirs(STATUS_DIR, exist_ok=True)
        print(f"Diretório de status: {STATUS_DIR}")
    except Exception as e:
        print(f"Erro ao criar diretório de status: {e}")
        exit(1)
    
    # Menu de opções
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--test-whatsapp":
        test_whatsapp_config()
        exit(0)
    
    monitor_main_script()