"""
test_model_pc.py — Testa full_detection_v2_nodfl.onnx direto no PC.
Usa RTX 3080 (device_id=1) via DirectML para não competir com Qwen na 3090.
"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))

import cv2
import numpy as np
import onnxruntime as ort

MODEL  = os.path.join(os.path.dirname(__file__), "models", "full_detection_v2_nodfl.onnx")
IMGDIR = os.path.join(os.path.dirname(__file__), "datasets", "brasil_animais")
CONF   = 0.20
IOU    = 0.45
IMGS_PER_CLASS = 3

CLASS_NAMES = {
    0:"person",1:"bicycle",2:"car",3:"motorcycle",4:"airplane",5:"bus",6:"train",
    7:"truck",8:"boat",9:"traffic light",10:"fire hydrant",11:"stop sign",
    12:"parking meter",13:"bench",14:"bird",15:"cat",16:"dog",17:"horse",
    18:"sheep",19:"cow",20:"elephant",21:"bear",22:"zebra",23:"giraffe",
    24:"backpack",25:"umbrella",26:"handbag",27:"tie",28:"suitcase",29:"frisbee",
    30:"skis",31:"snowboard",32:"sports ball",33:"kite",34:"baseball bat",
    35:"baseball glove",36:"skateboard",37:"surfboard",38:"tennis racket",
    39:"bottle",40:"wine glass",41:"cup",42:"fork",43:"knife",44:"spoon",
    45:"bowl",46:"banana",47:"apple",48:"sandwich",49:"orange",50:"broccoli",
    51:"carrot",52:"hot dog",53:"pizza",54:"donut",55:"cake",56:"chair",
    57:"couch",58:"potted plant",59:"bed",60:"dining table",61:"toilet",
    62:"tv",63:"laptop",64:"mouse",65:"remote",66:"keyboard",67:"cell phone",
    68:"microwave",69:"oven",70:"toaster",71:"sink",72:"refrigerator",73:"book",
    74:"clock",75:"vase",76:"scissors",77:"teddy bear",78:"hair drier",
    79:"toothbrush",
    80:"anta",81:"cachorro_do_mato",82:"capivara",83:"cutia",84:"gamba",
    85:"jacare",86:"jaguatirica",87:"lobo_guara",88:"mao_pelada",89:"quati",
    90:"seriema",91:"serpente",92:"tamandua_bandeira",93:"tamandua_mirim",94:"tatu",
}

# ── Anchors DFL decode (igual detection_engine.py) ────────────────────────────
def _make_anchors():
    al, sl = [], []
    for stride, gs in [(8,80),(16,40),(32,20)]:
        ys = np.arange(gs, dtype=np.float32) + 0.5
        xs = np.arange(gs, dtype=np.float32) + 0.5
        xv, yv = np.meshgrid(xs, ys)
        al.append(np.stack([xv.flatten(), yv.flatten()], axis=0))
        sl.append(np.full(gs*gs, stride, dtype=np.float32))
    return np.concatenate(al, axis=1), np.concatenate(sl)

_ANCHORS, _STRIDES = _make_anchors()

def _dfl_decode(raw_boxes):
    b = raw_boxes.reshape(4, 16, 8400)
    b = b - b.max(axis=1, keepdims=True)
    b = np.exp(b); b /= b.sum(axis=1, keepdims=True)
    bins = np.arange(16, dtype=np.float32)
    ltrb = (b * bins[None,:,None]).sum(axis=1)
    x1y1 = _ANCHORS - ltrb[:2]
    x2y2 = _ANCHORS + ltrb[2:]
    cxcy = (x1y1 + x2y2) * 0.5
    wh   = x2y2 - x1y1
    return np.concatenate([cxcy, wh], axis=0) * _STRIDES[None,:]

# ── Carregar modelo na RTX 3080 (device_id=1) ─────────────────────────────────
print("=" * 60)
print("TESTE DO MODELO — full_detection_v2_nodfl.onnx")
print(f"conf={CONF}  |  {IMGS_PER_CLASS} imgs/classe  |  GPU: RTX 3080 (device_id=1)")
print("=" * 60)

available = ort.get_available_providers()
if "DmlExecutionProvider" in available:
    providers = [("DmlExecutionProvider", {"device_id": 1}), "CPUExecutionProvider"]
    backend = "DirectML device_id=1 (RTX 3080)"
elif "CUDAExecutionProvider" in available:
    providers = [("CUDAExecutionProvider", {"device_id": 1}), "CPUExecutionProvider"]
    backend = "CUDA device_id=1 (RTX 3080)"
else:
    providers = ["CPUExecutionProvider"]
    backend = "CPU"

sess = ort.InferenceSession(MODEL, providers=providers)
input_name = sess.get_inputs()[0].name
out_names  = [o.name for o in sess.get_outputs()]
is_nodfl   = len(out_names) == 2
print(f"Modelo carregado | backend={backend} | outputs={out_names} | nodfl={is_nodfl}\n")

# ── Inferência ────────────────────────────────────────────────────────────────
def detect(frame):
    h, w = frame.shape[:2]
    img = cv2.resize(frame, (640, 640))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    blob = np.ascontiguousarray(img.transpose(2,0,1)[None])

    outs = sess.run(out_names, {input_name: blob})

    if is_nodfl:
        boxes_cxcywh = _dfl_decode(outs[0])
        scores = outs[1][0]
        output = np.concatenate([boxes_cxcywh, scores], axis=0).T
    else:
        output = np.squeeze(outs[0], axis=0).T if len(outs[0].shape)==3 else outs[0]

    scores_all = output[:, 4:]
    max_scores = scores_all.max(axis=1)
    mask = max_scores >= CONF
    if not mask.any():
        return []

    rows       = output[mask]
    confs      = max_scores[mask].tolist()
    class_ids  = scores_all[mask].argmax(axis=1).tolist()
    sx, sy     = w/640, h/640
    cx, cy     = rows[:,0], rows[:,1]
    bw, bh     = rows[:,2], rows[:,3]
    boxes      = np.stack([
        ((cx - bw*0.5)*sx).astype(int),
        ((cy - bh*0.5)*sy).astype(int),
        (bw*sx).astype(int),
        (bh*sy).astype(int),
    ], axis=1).tolist()

    indices = cv2.dnn.NMSBoxes(boxes, confs, CONF, IOU)
    results = []
    if len(indices) > 0:
        for i in indices.flatten():
            results.append({
                "cls": CLASS_NAMES.get(class_ids[i], f"cls{class_ids[i]}"),
                "conf": confs[i],
                "box": boxes[i],
            })
    return results

# ── Testar por classe ─────────────────────────────────────────────────────────
classes = sorted(os.listdir(IMGDIR)) if os.path.isdir(IMGDIR) else []
total_imgs = total_hits = 0

for cls_name in classes:
    cls_dir = os.path.join(IMGDIR, cls_name)
    if not os.path.isdir(cls_dir):
        continue
    imgs = sorted(glob.glob(os.path.join(cls_dir,"*.jpg")) +
                  glob.glob(os.path.join(cls_dir,"*.png")))[:IMGS_PER_CLASS]
    if not imgs:
        continue

    hits, dets_seen = 0, []
    for img_path in imgs:
        frame = cv2.imread(img_path)
        if frame is None:
            continue
        total_imgs += 1
        dets = detect(frame)
        if dets:
            hits += 1
            for d in dets:
                dets_seen.append(f"{d['cls']}({d['conf']:.2f})")

    total_hits += hits
    status = "OK" if hits > 0 else "--"
    det_str = "  ".join(dets_seen[:6]) if dets_seen else "nenhuma detecção"
    print(f"  [{status}] {cls_name:<22}  {hits}/{len(imgs)}  |  {det_str}")

print()
print("=" * 60)
pct = 100 * total_hits / total_imgs if total_imgs else 0
print(f"RESULTADO: {total_hits}/{total_imgs} imagens com detecção  ({pct:.0f}%)")
print("=" * 60)
