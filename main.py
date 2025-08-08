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
MODEL_PATH = "C:\\Users\\projeto\\Desktop\\bestn.pt"
# VIDEO_SOURCE = "C:\\Users\\12265587630\\Desktop\\g.mp4"
VIDEO_SOURCE = "rtsp://admin:123456789abc@10.12.8.63:554/cam/realmonitor?channel=1&subtype=0" # Example RTSP alternative
CONFIDENCE_THRESHOLD = 0.1  # Original: confianca_detectar_carro
FRAME_SKIP_INTERVAL = 1     # Original: intervalo_frames
ROTATION_ANGLES = [0, 15]   # Angles for plate rotation
OUTPUT_BASE_DIR_NAME = "placas_detectadas"
DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")
# --- End Constants ---

# results = {} # Unused

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
        detections_placas = detector_placa(frame_to_process)[0]
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
                    data_hoje_str = datetime.now().strftime("%Y-%m-%d")
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    car_id_generic = "placa" # Generic ID as no specific car tracking is implemented
                    placa_queue.put((placa_carro_crop.copy(), car_id_generic, frame_nmr, timestamp, ROTATION_ANGLES, data_hoje_str))
            else:
                print(f"Coordenadas da placa ({x1_p},{y1_p},{x2_p},{y2_p}) fora dos limites da imagem ({img_w}x{img_h}). Frame: {frame_nmr}")
        
        del frame_to_process # Explicitly delete frame to help memory management
        gc.collect()  # Força o coletor de lixo a liberar memória

finally:
    print("Finalizando o processamento...")
    # Finaliza a thread de salvamento
    placa_queue.put(None) # Signal worker thread to terminate
    thread_salvar.join() # Wait for worker thread to finish
    print("Thread de salvamento finalizada.")

    if cap.isOpened():
        cap.release()
        print("Recursos da câmera liberados.")
    cv2.destroyAllWindows() # Good practice, though not strictly necessary for non-GUI script
    print("Script encerrado.")