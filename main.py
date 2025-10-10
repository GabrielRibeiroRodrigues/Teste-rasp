import sys
from ultralytics import YOLO
# Compat: alguns checkpoints antigos referenciam 'ultralytics.utils'. Em versões antigas, utils ficava em 'ultralytics.yolo.utils'.
# Tente importar e, se não existir, crie um alias para manter compatibilidade durante o unpickling.
import requests
import time
import os

# --- CONFIGURAÇÃO ---
# URL do seu Webhook de Produção do n8n
N8N_WEBHOOK_URL = "https://campusinteligente.ifsuldeminas.edu.br/n8n/webhook/0615ade6-36bb-46b2-813b-84ada7c61a55"
HEARTBEAT_INTERVALO_SEGUNDOS = 900  # 30 segundos para detecção mais rápida de falhas

# Sistema de saúde do heartbeat
heartbeat_falhas_consecutivas = 0
MAX_FALHAS_HEARTBEAT = 3  # Máximo de falhas antes de considerar sistema crítico

# --- FUNÇÃO DE HEARTBEAT MELHORADA ---
def enviar_sinal_de_vida():
    """
    Envia uma requisição para o n8n para informar que o script está rodando.
    Inclui dados sobre status do sistema e verifica saúde real do loop principal.
    """
    global heartbeat_falhas_consecutivas
    
    try:
        # Verifica se o loop principal está realmente funcionando
        tempo_ultimo_frame = time.time() - getattr(enviar_sinal_de_vida, 'ultimo_frame_time', time.time())
        loop_saudavel = tempo_ultimo_frame < 60  # Se processou frame nos últimos 60s
        
        # Dados do sistema para enviar no heartbeat
        uptime = int(time.time() - start_time)
        payload = {
            "timestamp": time.time(),
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S'),
            "uptime_seconds": uptime,
            "uptime_minutes": round(uptime / 60, 1),
            "placas_detectadas": placas_detectadas_total,
            "placas_ignoradas": placas_ignoradas_total,
            "status": "healthy" if loop_saudavel else "degraded",
            "frame_atual": frame_nmr if 'frame_nmr' in globals() else 0,
            "pid": os.getpid(),
            "loop_saudavel": loop_saudavel,
            "tempo_ultimo_frame": tempo_ultimo_frame,
            "falhas_consecutivas": heartbeat_falhas_consecutivas
        }
        
        # Envia GET com dados como query parameters
        response = requests.get(N8N_WEBHOOK_URL, params=payload, timeout=15)
        response.raise_for_status()
        
        # Reset contador de falhas em caso de sucesso
        heartbeat_falhas_consecutivas = 0
        
        status_icon = "✅" if loop_saudavel else "⚠️"
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {status_icon} Heartbeat enviado - Status: {payload['status']}, Uptime: {payload['uptime_minutes']}min, Placas: {placas_detectadas_total}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        heartbeat_falhas_consecutivas += 1
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ❌ FALHA {heartbeat_falhas_consecutivas}: Erro ao enviar heartbeat para N8N. Erro: {e}")
        
        # Se muitas falhas consecutivas, considera sistema crítico
        if heartbeat_falhas_consecutivas >= MAX_FALHAS_HEARTBEAT:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🚨 SISTEMA CRÍTICO: {heartbeat_falhas_consecutivas} falhas consecutivas de heartbeat!")
        
        return False
try:
    import ultralytics.utils as _yu  # type: ignore
except Exception:
    try:
        import ultralytics.yolo.utils as _yu  # type: ignore
        sys.modules['ultralytics.utils'] = _yu  # cria alias para o caminho antigo
    except Exception as _e:
        print(
            f"Aviso: não foi possível preparar 'ultralytics.utils' ({_e}). O carregamento de pesos pode falhar.",
            file=sys.stderr,
        )
        _yu = None
        
import torch
from ultralytics.nn.tasks import DetectionModel
if hasattr(torch, "serialization") and hasattr(torch.serialization, "add_safe_globals"):
    try:
        torch.serialization.add_safe_globals([DetectionModel])
    except Exception as _e:
        print(f"Aviso: falha ao ajustar torch safe globals: {_e}", file=sys.stderr)
import cv2
import numpy as np 
from datetime import datetime
import gc
import threading
import queue
import json
import time
import hashlib

# --- Constants ---
MODEL_PATH = "C:\\Users\\projeto\\Desktop\\bestn.pt"
# VIDEO_SOURCE = "C:\\Users\\12265587630\\Desktop\\g.mp4"
VIDEO_SOURCE = "rtsp://admin:123456789abc@10.12.8.63:554/cam/realmonitor?channel=1&subtype=0" # Example RTSP alternative
CONFIDENCE_THRESHOLD = 0.1  # Original: confianca_detectar_carro
FRAME_SKIP_INTERVAL = 1     # Original: intervalo_frames
ROTATION_ANGLES = [0, 15]   # Angles for plate rotation
OUTPUT_BASE_DIR_NAME = "placas_detectadas"
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")

# Sistema de cooldown para evitar capturas duplicadas
COOLDOWN_SEGUNDOS = 3           # Tempo mínimo entre capturas da mesma placa
MAX_PLACAS_POR_MINUTO = 500      # Limite máximo de placas por minuto
HASH_IMAGE_SIZE = (64, 32)      # Tamanho para normalização do hash

# Estruturas de dados para controle de duplicatas
placas_recentes = {}            # {hash_placa: timestamp_ultima_captura}
capturas_por_minuto = []        # [timestamp1, timestamp2, ...]
placas_ignoradas_total = 0      # Contador de placas ignoradas por cooldown

# Configuração removida - usando apenas N8N heartbeat
# --- End Constants ---

# results = {} # Unused

# N8N heartbeat variables
start_time = time.time()
placas_detectadas_total = 0
ultimo_heartbeat_n8n = 0  # Controle para N8N

# Verifica se o arquivo de pesos existe; se não, tenta fallback para o arquivo local do repo
model_path_to_use = MODEL_PATH
if not os.path.isfile(model_path_to_use):
    repo_weight = os.path.join(os.path.dirname(__file__), "yolov8n.pt")
    if os.path.isfile(repo_weight):
        print(f"Aviso: arquivo de pesos não encontrado em '{MODEL_PATH}'. Usando fallback '{repo_weight}'.")
        model_path_to_use = repo_weight
    else:
        raise FileNotFoundError(
            f"Arquivo de pesos não encontrado em '{MODEL_PATH}' e fallback '{repo_weight}' inexistente."
        )

# Inicializa o modelo YOLO com tratamento de erro para mensagens mais claras
try:
    detector_placa = YOLO(model_path_to_use)
except Exception as e:
    raise RuntimeError(
        "Falha ao carregar pesos do YOLO. Possíveis causas: (1) incompatibilidade entre versões do PyTorch/Ultralytics; "
        "(2) arquivo de pesos corrompido; (3) mudança recente do torch.load (weights_only). "
        "Atualize ultralytics ou ajuste as versões de torch, ou re-exporte os pesos."
    ) from e
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    print(f"Erro ao abrir o vídeo: {VIDEO_SOURCE}")
    exit()

# veiculos = [2, 3, 5, 7]  # Unused
# confianca_detectar_carro = 0.1 # Moved to CONFIDENCE_THRESHOLD
frame_nmr = -1
ret = True # Controls the main loop, updated by cap.read()
# intervalo_frames = 1 # Moved to FRAME_SKIP_INTERVAL
# frame_anterior = -8 # Unused

# === SISTEMA DE COOLDOWN PARA PLACAS ===
def calcular_hash_placa(imagem_placa):
    """
    Calcula hash normalizado da placa para detecção de duplicatas.
    Redimensiona e converte para escala de cinza para maior robustez.
    """
    try:
        # 1. Redimensiona para tamanho fixo (elimina variações de tamanho)
        img_normalizada = cv2.resize(imagem_placa, HASH_IMAGE_SIZE)
        
        # 2. Converte para escala de cinza (elimina variações de cor)
        img_gray = cv2.cvtColor(img_normalizada, cv2.COLOR_BGR2GRAY)
        
        # 3. Calcula hash MD5 dos bytes da imagem
        hash_md5 = hashlib.md5(img_gray.tobytes()).hexdigest()
        
        return hash_md5
    except Exception as e:
        print(f"Erro ao calcular hash da placa: {e}")
        return None

def pode_salvar_placa(imagem_placa, debug=False):
    """
    Verifica se a placa pode ser salva baseado no sistema de cooldown.
    
    Returns:
        tuple: (pode_salvar: bool, motivo: str)
    """
    global placas_recentes, capturas_por_minuto, placas_ignoradas_total
    
    tempo_atual = time.time()
    
    # 1. Calcula hash da placa
    hash_placa = calcular_hash_placa(imagem_placa)
    if hash_placa is None:
        return True, "erro_hash"  # Se não conseguiu calcular hash, salva por segurança
    
    # 2. Verifica limite por minuto
    # Remove capturas antigas (> 60 segundos)
    capturas_por_minuto = [t for t in capturas_por_minuto if tempo_atual - t < 60]
    
    if len(capturas_por_minuto) >= MAX_PLACAS_POR_MINUTO:
        placas_ignoradas_total += 1
        return False, f"limite_minuto_{MAX_PLACAS_POR_MINUTO}"
    
    # 3. Verifica cooldown da placa específica
    if hash_placa in placas_recentes:
        tempo_ultima_captura = placas_recentes[hash_placa]
        tempo_desde_ultima = tempo_atual - tempo_ultima_captura
        
        if tempo_desde_ultima < COOLDOWN_SEGUNDOS:
            placas_ignoradas_total += 1
            if debug:
                print(f"Placa ignorada por cooldown: {tempo_desde_ultima:.1f}s < {COOLDOWN_SEGUNDOS}s")
            return False, f"cooldown_{tempo_desde_ultima:.1f}s"
    
    # 4. Pode salvar - atualiza os buffers
    placas_recentes[hash_placa] = tempo_atual
    capturas_por_minuto.append(tempo_atual)
    
    if debug:
        print(f"Placa aprovada para salvamento. Hash: {hash_placa[:8]}...")
    
    return True, "aprovada"

def limpar_buffers_antigos():
    """
    Remove entradas antigas dos buffers para evitar crescimento excessivo da memória.
    """
    global placas_recentes
    
    tempo_atual = time.time()
    
    # Remove placas que não vemos há mais de 5 minutos
    placas_antigas = [
        hash_placa for hash_placa, timestamp in placas_recentes.items()
        if tempo_atual - timestamp > 300  # 5 minutos
    ]
    
    for hash_placa in placas_antigas:
        del placas_recentes[hash_placa]
    
    if len(placas_antigas) > 0:
        print(f"Limpeza automática: removidas {len(placas_antigas)} placas antigas do buffer")

# Fila para salvar imagens das placas em thread separada
placa_queue = queue.Queue()

def salvar_placas_worker():
    while True:
        
        item = placa_queue.get()
        if item is None:
            break  # Sinal para encerrar a thread
        
        placa_carro_crop, car_id, current_frame_nmr, timestamp, angulos_rot, data_hoje_str = item
        (h, w) = placa_carro_crop.shape[:2]
        center = (w // 2, h // 2)
        
        pasta_base = os.path.join(DESKTOP_PATH, OUTPUT_BASE_DIR_NAME, data_hoje_str)
        if not os.path.exists(pasta_base):
            try:
                os.makedirs(pasta_base)
            except OSError as e:
                print(f"Erro ao criar diretório {pasta_base}: {e}")
                placa_queue.task_done()
                continue

        for angulo in angulos_rot:
            if angulo == 0:
                placa_rot = placa_carro_crop.copy()
            else:
                M = cv2.getRotationMatrix2D(center, -angulo, 1.0)
                placa_rot = cv2.warpAffine(placa_carro_crop, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            
            # FILTROS APLICADOS (Originalmente calculava gray/thresh mas não usava, removido para clareza)
            # Se precisar de processamento adicional na imagem salva, adicione aqui.
            # Exemplo:
            # placa_processada_gray = cv2.cvtColor(placa_rot, cv2.COLOR_BGR2GRAY)
            # _, placa_processada_thresh = cv2.threshold(placa_processada_gray, 64, 255, cv2.THRESH_BINARY_INV)
            # nome_arquivo = f"frame_{current_frame_nmr}_car_{car_id}_{timestamp}_ang{angulo}_thresh.png"
            # caminho_arquivo = os.path.join(pasta_base, nome_arquivo)
            # cv2.imwrite(caminho_arquivo, placa_processada_thresh)
            
            nome_arquivo = f"frame_{current_frame_nmr}_car_{car_id}_{timestamp}_ang{angulo}.png"
            caminho_arquivo = os.path.join(pasta_base, nome_arquivo)
            try:
                cv2.imwrite(caminho_arquivo, placa_rot)
            except Exception as e:
                print(f"Erro ao salvar imagem {caminho_arquivo}: {e}")
        placa_queue.task_done()

# Inicia a thread de salvamento
thread_salvar = threading.Thread(target=salvar_placas_worker, daemon=True)
thread_salvar.start()

# Envia primeiro sinal de vida para N8N
print("Iniciando automação de verificação de placas...")
print(f"[COOLDOWN] Sistema anti-duplicatas ativado:")
print(f"  - Cooldown por placa: {COOLDOWN_SEGUNDOS} segundos")
print(f"  - Limite por minuto: {MAX_PLACAS_POR_MINUTO} placas")
print(f"  - Tamanho do hash: {HASH_IMAGE_SIZE[0]}x{HASH_IMAGE_SIZE[1]} pixels")
print(f"  - N8N heartbeat: {HEARTBEAT_INTERVALO_SEGUNDOS} segundos")

enviar_sinal_de_vida()
ultimo_heartbeat_n8n = time.time()

try:
    while ret: # Loop continues as long as cap.read() is successful
        # data_e_hora_atuais = datetime.now() # Not directly used for naming here
        # data_e_hora_em_texto = data_e_hora_atuais.strftime('%Y-%m-%d %H:%M:%S') # Unused
        # data_atual = data_e_hora_atuais.strftime("%Y-%m-%d") # Unused, data_hoje is generated per detection

        frame_to_process = None
        # Loop to read/skip frames according to FRAME_SKIP_INTERVAL
        # Processes the last frame read in this sequence
        for _ in range(FRAME_SKIP_INTERVAL):
            frame_nmr += 1
            success, frame_read = cap.read() # 'success' will update the 'ret' for the main loop
            if not success:
                ret = False # Signal main loop to terminate
                print(f"Não foi possível ler o frame {frame_nmr} ou fim do vídeo.")
                break # Exit this inner loop
            frame_to_process = frame_read # Keep the latest successfully read frame
        
        if not ret: # If cap.read() failed in the inner loop
            break # Exit the main while loop

        if frame_to_process is None:
            # This might happen if FRAME_SKIP_INTERVAL is 0 or if ret is True but frame_read was None (unlikely)
            print(f"Nenhum frame válido para processar (frame_nmr: {frame_nmr}), mas 'ret' é True. Pulando.")
            continue

        # Detecção de placas usando apenas o modelo de placas
        detections_placas = detector_placa(frame_to_process, imgsz=416)[0]
        placas_detectadas = []
        for detection in detections_placas.boxes.data.tolist():
            x1, y1, x2, y2, confianca_atual, class_id = detection
            if confianca_atual >= CONFIDENCE_THRESHOLD:
                placas_detectadas.append([x1, y1, x2, y2, confianca_atual])

        # Salvar diretamente as placas detectadas
        for placa in placas_detectadas:
            x1_p, y1_p, x2_p, y2_p, _ = placa # Renamed to avoid conflict with frame_to_process shape
            # Ensure coordinates are integers and within bounds
            x1_p, y1_p, x2_p, y2_p = int(x1_p), int(y1_p), int(x2_p), int(y2_p)
            
            img_h, img_w = frame_to_process.shape[:2]
            if (0 <= x1_p < img_w and 0 <= y1_p < img_h and
                x1_p < x2_p <= img_w and y1_p < y2_p <= img_h):
                placa_carro_crop = frame_to_process[y1_p:y2_p, x1_p:x2_p]
                
                if placa_carro_crop.size != 0:
                    # Verifica sistema de cooldown antes de salvar
                    pode_salvar, motivo = pode_salvar_placa(placa_carro_crop)
                    
                    if pode_salvar:
                        data_hoje_str = datetime.now().strftime("%Y-%m-%d")
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        car_id_generic = "placa" # Generic ID as no specific car tracking is implemented
                        placa_queue.put((placa_carro_crop.copy(), car_id_generic, frame_nmr, timestamp, ROTATION_ANGLES, data_hoje_str))
                        placas_detectadas_total += 1  # Incrementa contador global
                    else:
                        # Log da placa ignorada (apenas a cada 100 para não poluir)
                        if placas_ignoradas_total % 100 == 0:
                            print(f"[COOLDOWN] {placas_ignoradas_total} placas ignoradas. Última: {motivo} | Frame: {frame_nmr}")
            else:
                print(f"Coordenadas da placa ({x1_p},{y1_p},{x2_p},{y2_p}) fora dos limites da imagem ({img_w}x{img_h}). Frame: {frame_nmr}")
        
        # Atualiza timestamp do último frame para heartbeat
        enviar_sinal_de_vida.ultimo_frame_time = time.time()
        
        # Lógica para enviar sinal de vida para N8N periodicamente
        current_time = time.time()
        if current_time - ultimo_heartbeat_n8n > HEARTBEAT_INTERVALO_SEGUNDOS:
            heartbeat_sucesso = enviar_sinal_de_vida()
            ultimo_heartbeat_n8n = current_time
            
            # Se falhou muitas vezes, pode indicar problema de conectividade
            if not heartbeat_sucesso and heartbeat_falhas_consecutivas >= MAX_FALHAS_HEARTBEAT:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Continuando execução apesar das falhas de heartbeat...")
        
        # Limpeza automática dos buffers a cada 100 frames
        if frame_nmr % 100 == 0:
            limpar_buffers_antigos()
        
        del frame_to_process # Explicitly delete frame to help memory management
        gc.collect()  # Força o coletor de lixo a liberar memória

finally:
    print("Finalizando o processamento...")
    
    # Envia último heartbeat com status de finalização
    try:
        uptime = int(time.time() - start_time)
        payload_final = {
            "timestamp": time.time(),
            "datetime": time.strftime('%Y-%m-%d %H:%M:%S'),
            "uptime_seconds": uptime,
            "status": "stopping",
            "placas_detectadas": placas_detectadas_total,
            "pid": os.getpid(),
            "motivo_parada": "finalizacao_normal"
        }
        requests.get(N8N_WEBHOOK_URL, params=payload_final, timeout=10)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 🔄 Heartbeat final enviado - Status: stopping")
    except:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ⚠️ Não foi possível enviar heartbeat final")
    
    # Estatísticas finais do sistema de cooldown
    uptime_total = time.time() - start_time
    print(f"\n=== ESTATÍSTICAS FINAIS ===")
    print(f"Tempo de execução: {uptime_total/60:.1f} minutos")
    print(f"Placas salvas: {placas_detectadas_total}")
    print(f"Placas ignoradas (cooldown): {placas_ignoradas_total}")
    print(f"Falhas de heartbeat: {heartbeat_falhas_consecutivas}")
    if placas_detectadas_total + placas_ignoradas_total > 0:
        taxa_aproveitamento = (placas_detectadas_total / (placas_detectadas_total + placas_ignoradas_total)) * 100
        print(f"Taxa de aproveitamento: {taxa_aproveitamento:.1f}%")
    print(f"Placas únicas no buffer: {len(placas_recentes)}")
    print("===========================\n")
    
    # Finaliza a thread de salvamento
    placa_queue.put(None) # Signal worker thread to terminate
    thread_salvar.join() # Wait for worker thread to finish
    print("Thread de salvamento finalizada.")

    if cap.isOpened():
        cap.release()
        print("Recursos da câmera liberados.")
    cv2.destroyAllWindows() # Good practice, though not strictly necessary for non-GUI script
    print("Script encerrado.")