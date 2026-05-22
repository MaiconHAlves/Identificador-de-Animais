"""
Teste de webcam local — DetectionEngine com câmera real.
Mostra FPS, bounding boxes e confiança. Pressione Q para sair.
"""
import cv2
import time
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.detection_engine import DetectionEngine

CONF_THRESHOLD = 0.05
IOU_THRESHOLD  = 0.45
CAM_ID         = 0  # mude para 1, 2... se a webcam não abrir

# 95 classes: 80 COCO + 15 espécies brasileiras
ALL_CLASSES = [
    "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat",
    "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
    "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
    "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
    "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
    "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
    "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
    "couch","potted plant","bed","dining table","toilet","tv","laptop","mouse",
    "remote","keyboard","cell phone","microwave","oven","toaster","sink",
    "refrigerator","book","clock","vase","scissors","teddy bear","hair drier","toothbrush",
    "anta","cachorro_do_mato","capivara","cutia","gamba","jacare","jaguatirica",
    "lobo_guara","mao_pelada","quati","seriema","serpente","tamandua_bandeira",
    "tamandua_mirim","tatu",
]

# Cores: person=amarelo, veículos=roxo, animais BR=verde, outros=ciano
def get_color(class_id):
    if class_id == 0:               return (0, 220, 255)   # person — amarelo
    if class_id in (1,2,3,5,7):    return (180, 100, 255)  # veículos — roxo
    if class_id >= 80:              return (0, 255, 80)     # BR — verde
    return (0, 220, 220)                                    # outros — ciano


def label_name(class_id, _source):
    return ALL_CLASSES[class_id] if class_id < len(ALL_CLASSES) else f"cls{class_id}"


def draw(frame, detections):
    for d in detections:
        x, y, w, h = d["box"]
        conf = d["confidence"]
        name = label_name(d["label_id"], d["source"])
        color = get_color(d["label_id"])
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame, f"{name} {conf:.2f}", (x, y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)


def main():
    # Modelo dual — Fase 1 (catastrophic forgetting do COCO no fulldet, compensado pelo yolov8n COCO)
    coco_path = "models/coco_yolov8n_nc80_v0_i320_nodfl.onnx"
    br_path   = "models/fulldet_yolov8n_nc95_v3_m692_i320_nodfl.onnx"

    model_path = []
    if os.path.exists(coco_path):
        model_path.append(coco_path)
        print(f"[OK] COCO model: {coco_path}")
    if os.path.exists(br_path):
        model_path.append(br_path)
        print(f"[OK] BR model:   {br_path}")
    if not model_path:
        print("[ERRO] Nenhum modelo encontrado.")
        sys.exit(1)

    engine = DetectionEngine(
        model_paths=model_path,
        conf_threshold=CONF_THRESHOLD,
        iou_threshold=IOU_THRESHOLD,
    )

    cap = cv2.VideoCapture(CAM_ID)
    if not cap.isOpened():
        print(f"[ERRO] Câmera {CAM_ID} não encontrada.")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("[OK] Câmera aberta. Pressione Q para sair.")

    # Shared state between capture and inference threads
    lock        = threading.Lock()
    last_frame  = [None]
    last_dets   = [[]]
    stop_flag   = [False]
    inf_fps_val = [0.0]

    def inference_loop():
        inf_t = time.perf_counter()
        inf_n = 0
        while not stop_flag[0]:
            with lock:
                frame = last_frame[0]
            if frame is None:
                time.sleep(0.001)
                continue
            dets = engine.detect(frame)
            inf_n += 1
            now = time.perf_counter()
            if now - inf_t >= 1.0:
                with lock:
                    inf_fps_val[0] = inf_n / (now - inf_t)
                inf_n = 0
                inf_t = now
            with lock:
                last_dets[0] = dets

    t = threading.Thread(target=inference_loop, daemon=True)
    t.start()

    fps_t = time.perf_counter()
    fps_count = 0
    fps_display = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        with lock:
            last_frame[0] = frame.copy()
            dets = last_dets[0]

        draw(frame, dets)

        fps_count += 1
        now = time.perf_counter()
        if now - fps_t >= 1.0:
            fps_display = fps_count / (now - fps_t)
            fps_count = 0
            fps_t = now

        with lock:
            inf_fps = inf_fps_val[0]
        cv2.putText(frame, f"CAM: {fps_display:.1f}  INF: {inf_fps:.1f}  Targets: {len(dets)}",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2, cv2.LINE_AA)

        cv2.imshow("Animal Detector — webcam test", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    stop_flag[0] = True
    t.join(timeout=2.0)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
