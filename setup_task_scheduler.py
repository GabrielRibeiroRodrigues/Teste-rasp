# Configurador do Windows Task Scheduler para GuaritaIdentificador
# Execute este script como Administrador para configurar o restart automático

import subprocess
import sys
import os
from datetime import datetime

def is_admin():
    """Verifica se o script está sendo executado como administrador"""
    try:
        return os.getuid() == 0
    except AttributeError:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

def create_scheduled_task():
    """Cria a tarefa agendada no Windows Task Scheduler"""
    
    # Caminhos
    script_path = r"C:\Users\projeto\GuaritaIdentificador09-07\restart_guarita.bat"
    task_name = "GuaritaIdentificador_Restart"
    
    print("🏢 Configurando Windows Task Scheduler para GuaritaIdentificador...")
    print("=" * 60)
    
    # Verifica se o script .bat existe
    if not os.path.exists(script_path):
        print(f"❌ ERRO: Script {script_path} não encontrado!")
        return False
    
    try:
        # Remove tarefa existente se houver
        print("🗑️ Removendo tarefa existente (se houver)...")
        subprocess.run([
            "schtasks", "/delete", "/tn", task_name, "/f"
        ], capture_output=True, text=True)
        
        # Cria nova tarefa agendada
        print("⏰ Criando nova tarefa agendada...")
        
        command = [
            "schtasks", "/create",
            "/tn", task_name,                              # Nome da tarefa
            "/tr", script_path,                            # Script a executar
            "/sc", "daily",                                # Frequência: diariamente
            "/st", "03:00",                                # Horário: 03:00
            "/ru", "SYSTEM",                               # Executar como SYSTEM
            "/rl", "HIGHEST",                              # Nível de privilégio máximo
            "/f"                                           # Força criação (sobrescreve)
        ]
        
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Tarefa agendada criada com sucesso!")
            print(f"📅 Agendamento: Todos os dias às 03:00")
            print(f"🎯 Script: {script_path}")
            print(f"👤 Usuário: SYSTEM (máximos privilégios)")
            
            # Verifica se a tarefa foi criada
            print("\n🔍 Verificando tarefa criada...")
            verify_result = subprocess.run([
                "schtasks", "/query", "/tn", task_name
            ], capture_output=True, text=True)
            
            if verify_result.returncode == 0:
                print("✅ Tarefa verificada com sucesso!")
                return True
            else:
                print("⚠️ Tarefa criada mas não foi possível verificar")
                return True
                
        else:
            print(f"❌ Erro ao criar tarefa: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def show_task_info():
    """Mostra informações sobre como gerenciar a tarefa"""
    task_name = "GuaritaIdentificador_Restart"
    
    print("\n" + "=" * 60)
    print("📋 COMANDOS ÚTEIS PARA GERENCIAR A TAREFA:")
    print("=" * 60)
    
    print(f"🔍 Ver detalhes da tarefa:")
    print(f'   schtasks /query /tn "{task_name}" /fo LIST /v')
    
    print(f"\n▶️ Executar tarefa manualmente (teste):")
    print(f'   schtasks /run /tn "{task_name}"')
    
    print(f"\n⏸️ Desabilitar tarefa:")
    print(f'   schtasks /change /tn "{task_name}" /disable')
    
    print(f"\n▶️ Habilitar tarefa:")
    print(f'   schtasks /change /tn "{task_name}" /enable')
    
    print(f"\n🗑️ Remover tarefa:")
    print(f'   schtasks /delete /tn "{task_name}" /f')
    
    print(f"\n🖥️ Abrir Task Scheduler GUI:")
    print(f"   taskschd.msc")
    
    print("\n" + "=" * 60)
    print("💡 DICAS:")
    print("- Execute este script como Administrador")
    print("- A tarefa será executada mesmo se ninguém estiver logado")
    print("- Logs do restart ficarão em restart_log.txt")
    print("- Para testar, execute manualmente uma vez")

def main():
    print("🚀 Configurador do Windows Task Scheduler")
    print("   GuaritaIdentificador - Restart Automático às 03:00")
    print("=" * 60)
    
    # Verifica se é administrador
    if not is_admin():
        print("❌ ERRO: Este script precisa ser executado como Administrador!")
        print("💡 SOLUÇÃO:")
        print("   1. Abra o Prompt de Comando como Administrador")
        print("   2. Navegue até a pasta do projeto")
        print("   3. Execute: python setup_task_scheduler.py")
        input("\nPressione Enter para sair...")
        return
    
    # Cria a tarefa
    success = create_scheduled_task()
    
    if success:
        show_task_info()
        print("\n🎉 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("🕒 O sistema será reiniciado automaticamente todos os dias às 03:00")
    else:
        print("\n❌ FALHA NA CONFIGURAÇÃO!")
        print("💡 Verifique se você está executando como Administrador")
    
    input("\nPressione Enter para sair...")

if __name__ == "__main__":
    main()