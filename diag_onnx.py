"""
Diagnóstico do ONNX nodfl: confirma I/O shapes + roda inferência num frame real.
Uso:
  py -3.12 diag_onnx.py                       # default = nodfl atual
  py -3.12 diag_onnx.py <caminho_do_onnx>     # qualquer ONNX (ex: best.onnx pré-strip)
"""
import onnxruntime as ort
import numpy as np
import cv2
import sys
import os

MODEL = sys.argv[1] if len(sys.argv) > 1 else "models/fulldet_yolov8n_nc95_v3_m692_nodfl.onnx"

print("=" * 70)
print(f"Diagnóstico: {MODEL}")
print("=" * 70)

if not os.path.exists(MODEL):
    print(f"[ERRO] Modelo não existe: {MODEL}")
    sys.exit(1)

# 1. Carregar
providers = ort.get_available_providers()
print(f"\nProviders disponíveis: {providers}")
ep = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if 'CUDAExecutionProvider' in providers else ['CPUExecutionProvider']
sess = ort.InferenceSession(MODEL, providers=ep)
print(f"Provider ativo: {sess.get_providers()[0]}")

# 2. I/O shapes
print("\n--- Inputs ---")
for i in sess.get_inputs():
    print(f"  {i.name}  shape={i.shape}  dtype={i.type}")
print("--- Outputs ---")
for o in sess.get_outputs():
    print(f"  {o.name}  shape={o.shape}  dtype={o.type}")

# 3. Inferência com frame da webcam (frame real)
print("\n--- Capturando frame da webcam (CAM 0) ---")
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[AVISO] Câmera 0 não abriu — usando frame sintético (uniform).")
    frame = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)
else:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("[AVISO] Falha ao ler frame — usando sintético.")
        frame = (np.random.rand(480, 640, 3) * 255).astype(np.uint8)
    else:
        print(f"Frame capturado: shape={frame.shape} dtype={frame.dtype}")

# 4. Pré-processa (igual ao DetectionEngine)
blob = cv2.dnn.blobFromImage(frame, scalefactor=1.0/255.0, size=(640, 640),
                              mean=(0,0,0), swapRB=True, crop=False)
print(f"Blob: shape={blob.shape} dtype={blob.dtype} min={blob.min():.4f} max={blob.max():.4f}")

# 5. Roda inferência
input_name = sess.get_inputs()[0].name
outs = sess.run(None, {input_name: blob})
print(f"\n--- Outputs da inferência (n={len(outs)}) ---")
for i, o in enumerate(outs):
    print(f"  out[{i}]: shape={o.shape} dtype={o.dtype} min={o.min():.4f} max={o.max():.4f} mean={o.mean():.4f}")

# 6. Identificar boxes vs scores (suporta nodfl=2 outputs e full=1 output)
raw_scores = None
if len(outs) == 2:
    # Modelo nodfl: 2 outputs — boxes [1,64,N] + scores [1,nc,N]
    if outs[0].shape[1] == 64:
        raw_boxes, raw_scores = outs[0], outs[1]
        print(f"\nIdentificado (nodfl): out[0]=boxes (64 canais DFL), out[1]=scores")
    else:
        raw_boxes, raw_scores = outs[1], outs[0]
        print(f"\nIdentificado (nodfl): out[1]=boxes (64 canais DFL), out[0]=scores")
elif len(outs) == 1:
    # Modelo full: 1 output [1, 4+nc, N] — primeiras 4 linhas = boxes decoded, restantes = scores
    full = outs[0]
    print(f"\nIdentificado (full DFL nativo): out[0] shape={full.shape}")
    if full.ndim == 3 and full.shape[1] >= 5:
        raw_scores = full[:, 4:, :]   # tudo exceto as 4 primeiras linhas (boxes)
        print(f"  Scores extraídos: shape={raw_scores.shape}  (4+nc canais; nc={raw_scores.shape[1]})")

if raw_scores is not None:
    # 7. Análise dos scores
    print(f"\n--- Análise dos scores (raw_scores[0]) ---")
    s = raw_scores[0]
    print(f"  shape={s.shape}  min={s.min():.4f}  max={s.max():.4f}  mean={s.mean():.4f}")
    print(f"  scores >= 0.01: {(s >= 0.01).sum()}")
    print(f"  scores >= 0.05: {(s >= 0.05).sum()}")
    print(f"  scores >= 0.10: {(s >= 0.10).sum()}")
    print(f"  scores >= 0.25: {(s >= 0.25).sum()}")

    # Top-5 scores e suas classes
    if s.shape[0] > 0 and s.shape[1] > 0:
        if s.shape[0] < s.shape[1]:
            print(f"  Layout assumido: [nc={s.shape[0]}, anchors={s.shape[1]}]  (correto p/ engine atual)")
            max_per_anchor = s.max(axis=0)
            argmax_class   = s.argmax(axis=0)
        else:
            print(f"  Layout assumido: [anchors={s.shape[0]}, nc={s.shape[1]}]  (TRANSPOSED — engine pode falhar!)")
            max_per_anchor = s.max(axis=1)
            argmax_class   = s.argmax(axis=1)

        top5_idx = np.argsort(max_per_anchor)[-5:][::-1]
        print(f"\n  Top-5 anchors por max_score:")
        for idx in top5_idx:
            print(f"    anchor[{idx}]: max_score={max_per_anchor[idx]:.4f} class_id={argmax_class[idx]}")

print("\n" + "=" * 70)
print("FIM do diagnóstico")
print("=" * 70)
