import sys
from ultralytics import YOLO
# Compat: alguns checkpoints antigos referenciam 'ultralytics.utils'. Em versões antigas, utils ficava em 'ultralytics.yolo.utils'.
# Tente importar e, se não existir, crie um alias para manter compatibilidade durante o unpickling.
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
import os
import threading
import queue

# --- Constants ---
VEHICLE_MODEL_PATH = "yolov8n.pt"  # Modelo pré-treinado do Ultralytics para veículos
# VIDEO_SOURCE = "C:\\Users\\12265587630\\Desktop\\g.mp4"
VIDEO_SOURCE = "rtsp://admin:123456789abc@10.12.8.63:554/cam/realmonitor?channel=1&subtype=0" # Example RTSP alternative
CONFIDENCE_THRESHOLD_VEHICLE = 0.3  # Confiança para detectar veículos
FRAME_SKIP_INTERVAL = 1     # Original: intervalo_frames
OUTPUT_BASE_DIR_NAME = "carros_detectados"
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
MAX_FILES_PER_DAY = 20000  # Limite máximo de arquivos por pasta diária
# Classes de veículos no COCO dataset: car=2, motorcycle=3, bus=5, truck=7
VEHICLE_CLASSES = [2, 3, 5, 7]
# --- End Constants ---

# results = {} # Unused

# Inicializa apenas o modelo de veículos
try:
    detector_veiculo = YOLO(VEHICLE_MODEL_PATH)
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

# Fila para salvar imagens dos veículos em thread separada
veiculo_queue = queue.Queue()

def salvar_veiculos_worker():
    while True:
        item = veiculo_queue.get()
        if item is None:
            break  # Sinal para encerrar a thread
        
        veiculo_crop, car_id, current_frame_nmr, timestamp, data_hoje_str = item
        
        pasta_base = os.path.join(DESKTOP_PATH, OUTPUT_BASE_DIR_NAME, data_hoje_str)
        if not os.path.exists(pasta_base):
            try:
                os.makedirs(pasta_base)
            except OSError as e:
                print(f"Erro ao criar diretório {pasta_base}: {e}")
                veiculo_queue.task_done()
                continue

        # Verifica se já existem muitos arquivos na pasta do dia
        try:
            arquivos_existentes = len([f for f in os.listdir(pasta_base) if f.endswith('.png')])
            if arquivos_existentes >= MAX_FILES_PER_DAY:
                print(f"Limite de {MAX_FILES_PER_DAY} arquivos atingido para {data_hoje_str}. Pulando salvamento.")
                veiculo_queue.task_done()
                continue
        except OSError as e:
            print(f"Erro ao contar arquivos em {pasta_base}: {e}")
            veiculo_queue.task_done()
            continue

        nome_arquivo = f"frame_{current_frame_nmr}_{car_id}_{timestamp}.png"
        caminho_arquivo = os.path.join(pasta_base, nome_arquivo)
        try:
            cv2.imwrite(caminho_arquivo, veiculo_crop)
        except Exception as e:
            print(f"Erro ao salvar imagem {caminho_arquivo}: {e}")
        veiculo_queue.task_done()

# Inicia a thread de salvamento
thread_salvar = threading.Thread(target=salvar_veiculos_worker, daemon=True)
thread_salvar.start()

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

        # Primeiro detecta veículos usando o modelo pré-treinado
        detections_veiculos = detector_veiculo(frame_to_process)[0]
        veiculos_detectados = []
        for detection in detections_veiculos.boxes.data.tolist():
            x1, y1, x2, y2, confianca_atual, class_id = detection
            if confianca_atual >= CONFIDENCE_THRESHOLD_VEHICLE and int(class_id) in VEHICLE_CLASSES:
                veiculos_detectados.append([int(x1), int(y1), int(x2), int(y2), confianca_atual, int(class_id)])

        # Para cada veículo detectado, salva a imagem
        for veiculo in veiculos_detectados:
            x1_v, y1_v, x2_v, y2_v, conf_v, class_v = veiculo
            
            # Extrai a região do veículo
            img_h, img_w = frame_to_process.shape[:2]
            x1_v = max(0, x1_v)
            y1_v = max(0, y1_v)
            x2_v = min(img_w, x2_v)
            y2_v = min(img_h, y2_v)
            
            veiculo_crop = frame_to_process[y1_v:y2_v, x1_v:x2_v]
            
            if veiculo_crop.size == 0:
                continue
            
            data_hoje_str = datetime.now().strftime("%Y-%m-%d")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # Mapeia class_id para nome do veículo
            vehicle_names = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}
            vehicle_name = vehicle_names.get(class_v, f"vehicle_{class_v}")
            car_id = f"{vehicle_name}_{x1_v}_{y1_v}"
            
            veiculo_queue.put((veiculo_crop.copy(), car_id, frame_nmr, timestamp, data_hoje_str))
            
            print(f"Frame {frame_nmr}: {vehicle_name} detectado - confiança: {conf_v:.2f}")
        
        print(f"Frame {frame_nmr}: {len(veiculos_detectados)} veículos detectados")
        
        del frame_to_process # Explicitly delete frame to help memory management
        gc.collect()  # Força o coletor de lixo a liberar memória

finally:
    print("Finalizando o processamento...")
    # Finaliza a thread de salvamento
    veiculo_queue.put(None) # Signal worker thread to terminate
    thread_salvar.join() # Wait for worker thread to finish
    print("Thread de salvamento finalizada.")

    if cap.isOpened():
        cap.release()
        print("Recursos da câmera liberados.")
    cv2.destroyAllWindows() # Good practice, though not strictly necessary for non-GUI script
    print("Script encerrado.")