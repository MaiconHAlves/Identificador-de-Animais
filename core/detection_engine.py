import cv2
import numpy as np
import os

PERSON_CLASS_ID = 0   # classe "person" no modelo 95-classes (COCO index 0)
CROSS_IOU_THRESH = 0.30  # overlap above this suppresses hybrid detection


def _make_anchors_and_strides(w, h):
    anchors_list = []
    strides_list = []
    for stride in [8, 16, 32]:
        gs_h = h // stride
        gs_w = w // stride
        ys = np.arange(gs_h, dtype=np.float32) + 0.5
        xs = np.arange(gs_w, dtype=np.float32) + 0.5
        xv, yv = np.meshgrid(xs, ys)
        anchors_list.append(np.stack([xv.flatten(), yv.flatten()], axis=0))
        strides_list.append(np.full(gs_h * gs_w, stride, dtype=np.float32))
    anchors = np.concatenate(anchors_list, axis=1)
    strides = np.concatenate(strides_list)
    return anchors, strides





def _dfl_decode(raw_boxes, anchors, strides):
    """DFL decode: [1,64,N] -> [4,N] cx,cy,w,h in pixel coords."""
    n_anchors = anchors.shape[1]
    b = raw_boxes.reshape(4, 16, n_anchors)
    b = b - b.max(axis=1, keepdims=True)
    b = np.exp(b)
    b = b / b.sum(axis=1, keepdims=True)
    bins = np.arange(16, dtype=np.float32)
    ltrb = (b * bins[None, :, None]).sum(axis=1)
    x1y1 = anchors - ltrb[:2, :]
    x2y2 = anchors + ltrb[2:, :]
    cx_cy = (x1y1 + x2y2) * 0.5
    wh    = x2y2 - x1y1
    return np.concatenate([cx_cy, wh], axis=0) * strides[None, :]


def _iou(boxA, boxB):
    """IoU between two [x, y, w, h] boxes."""
    ax1, ay1 = boxA[0], boxA[1]
    ax2, ay2 = boxA[0] + boxA[2], boxA[1] + boxA[3]
    bx1, by1 = boxB[0], boxB[1]
    bx2, by2 = boxB[0] + boxB[2], boxB[1] + boxB[3]
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    areaA = boxA[2] * boxA[3]
    areaB = boxB[2] * boxB[3]
    return inter / (areaA + areaB - inter)


def _is_android():
    try:
        from kivy.utils import platform as _plat
        return _plat == 'android'
    except Exception:
        return os.path.exists('/system/bin/app_process') or 'ANDROID_ARGUMENT' in os.environ


class DetectionEngine:
    """
    Android  → cv2.dnn CPU (OpenCV 4.5.1 shipped with p4a).
    Desktop  → onnxruntime with CUDAExecutionProvider (RTX 3090).
    _nodfl models: 2 outputs [1,64,8400] + [1,nc,8400]; DFL decoded in Python.
    """
    def __init__(self, model_paths=["yolov8n.onnx"], conf_threshold=0.25, iou_threshold=0.45):
        self.conf_threshold = conf_threshold
        self.iou_threshold  = iou_threshold
        self.input_width    = 640
        self.input_height   = 640
        self.nc             = 95  # Número de classes (COCO + Fauna BR)
        self.anchors, self.strides = _make_anchors_and_strides(self.input_width, self.input_height)
        self.nets = []
        self._dbg_calls = 0  # Contador para logs de debug

        self._android = _is_android()
        print(f"[DEBUG] Plataforma: {'ANDROID' if self._android else 'DESKTOP'}")

        if self._android:
            self._load_opencv(model_paths)
        else:
            self._load_ort(model_paths)

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------
    def _load_opencv(self, model_paths):
        for path in model_paths:
            try:
                net = cv2.dnn.readNetFromONNX(path)
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                out_names = net.getUnconnectedOutLayersNames()
                is_nodfl  = len(out_names) == 2
                self.nets.append({"net": net, "name": self._model_name(path),
                                  "nodfl": is_nodfl, "backend": "opencv"})
                print(f"Engine [{path}] carregada (OpenCV CPU) mode={'nodfl' if is_nodfl else 'full'} out_names={out_names}")
            except Exception as e:
                print(f"Aviso: falha ao carregar {path}: {e}")

    def _load_ort(self, model_paths):
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            if 'CUDAExecutionProvider' in available:
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
                backend_label = "ORT CUDA"
            elif 'DmlExecutionProvider' in available:
                providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
                backend_label = "ORT DirectML"
            else:
                providers = ['CPUExecutionProvider']
                backend_label = "ORT CPU"
        except ImportError:
            print("onnxruntime não encontrado — usando cv2.dnn CPU")
            self._load_opencv(model_paths)
            return

        for path in model_paths:
            try:
                sess = ort.InferenceSession(path, providers=providers)
                input_name = sess.get_inputs()[0].name
                out_names  = [o.name for o in sess.get_outputs()]
                is_nodfl   = len(out_names) == 2
                self.nets.append({"net": sess, "input_name": input_name,
                                  "out_names": out_names,
                                  "name": self._model_name(path),
                                  "nodfl": is_nodfl, "backend": "ort"})
                active_ep = sess.get_providers()[0]
                print(f"Engine [{path}] carregada ({backend_label} / {active_ep}) mode={'nodfl' if is_nodfl else 'full'}")
            except Exception as e:
                print(f"Aviso: falha ao carregar {path}: {e}")

    @staticmethod
    def _model_name(path):
        p = path.lower()
        if "animal_wild_br" in p:
            return "br_specialist"
        if "unified" in p:
            return "unified"
        if "hybrid" in p or "road" in p:
            return "custom"
        return "global"

    # ------------------------------------------------------------------
    # Inference helpers
    # ------------------------------------------------------------------
    def _forward_ort(self, engine, blob):
        outs = engine["net"].run(engine["out_names"], {engine["input_name"]: blob})
        return outs

    def _forward_opencv(self, engine, blob):
        engine["net"].setInput(blob)
        if engine["nodfl"]:
            out_names = engine["net"].getUnconnectedOutLayersNames()
            return engine["net"].forward(out_names)
        return [engine["net"].forward()]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect(self, frame):
        self._dbg_calls += 1
        if frame is None or frame.size == 0:
            return []

        h_orig, w_orig = frame.shape[:2]
        all_results = []

        blob = cv2.dnn.blobFromImage(
            frame, 
            scalefactor=1.0/255.0, 
            size=(self.input_width, self.input_height), 
            mean=(0,0,0), 
            swapRB=True, 
            crop=False
        )

        for engine in self.nets:
            try:
                if engine["backend"] == "ort":
                    outs = self._forward_ort(engine, blob)
                else:
                    outs = self._forward_opencv(engine, blob)

                if engine["nodfl"]:
                    if len(outs) < 2:
                        print(f"detect [{engine['name']}]: nodfl esperava 2 outputs, recebeu {len(outs)}")
                        continue
                    if self._dbg_calls <= 3:
                        print(f"[OUTS-DBG] outs[0].shape={outs[0].shape} outs[1].shape={outs[1].shape}")
                    # shape[1]==64 = 4 canais × 16 bins DFL → raw_boxes
                    if outs[0].shape[1] == 64:
                        raw_boxes, raw_scores = outs[0], outs[1]
                    else:
                        raw_scores, raw_boxes = outs[0], outs[1]
                        
                    if raw_boxes is None or raw_boxes.size == 0:
                        continue

                    if self._dbg_calls <= 3:
                        print(f"[BOXES-DBG] shape={raw_boxes.shape} min={raw_boxes.min():.4f} max={raw_boxes.max():.4f}")
                        print(f"[SCORES-RAW-DBG] shape={raw_scores.shape} min={raw_scores.min():.4f} max={raw_scores.max():.4f}")

                    boxes_cxcywh = _dfl_decode(raw_boxes, self.anchors, self.strides)
                    s = raw_scores[0]
                    if self._dbg_calls <= 3:
                        print(f"[SCORES-DBG] min={s.min():.4f} max={s.max():.4f} shape={s.shape}")
                    # Apply sigmoid if outputs are raw logits (probabilities are always >= 0)
                    if s.min() < 0:
                        s = 1.0 / (1.0 + np.exp(-np.clip(s, -88.0, 88.0)))
                    scores = s
                    output       = np.concatenate([boxes_cxcywh, scores], axis=0).T
                else:
                    raw = outs[0]
                    if raw is None or raw.size == 0:
                        continue
                    output = np.squeeze(raw, axis=0).T if len(raw.shape) == 3 else raw

            except cv2.error as e:
                print(f"detect cv2.error [{engine['name']}]: {e}")
                continue
            except Exception as e:
                print(f"detect erro [{engine['name']}]: {e}")
                continue

            # Vectorized postprocess — replaces 8400-iteration Python loop
            scores_all  = output[:, 4:]                           # [8400, nc]
            max_scores  = scores_all.max(axis=1)                  # [8400]
            mask        = max_scores >= self.conf_threshold
            if not mask.any():
                if self._dbg_calls % 10 == 0:
                    print(f"detect [{engine['name']}]: shape={output.shape} max_score={max_scores.max():.3f} hits=0")
                continue

            rows        = output[mask]
            confidences = max_scores[mask].tolist()
            class_ids   = scores_all[mask].argmax(axis=1).tolist()
            sx, sy      = w_orig / self.input_width, h_orig / self.input_height
            cx, cy      = rows[:, 0], rows[:, 1]
            bw, bh      = rows[:, 2], rows[:, 3]
            lefts       = ((cx - bw * 0.5) * sx).astype(int)
            tops        = ((cy - bh * 0.5) * sy).astype(int)
            widths      = (bw * sx).astype(int)
            heights     = (bh * sy).astype(int)
            boxes       = np.stack([lefts, tops, widths, heights], axis=1).tolist()

            if self._dbg_calls % 10 == 0:
                print(f"detect [{engine['name']}]: shape={output.shape} max_score={max_scores.max():.3f} hits={len(boxes)}")

            indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
            if len(indices) > 0:
                for i in indices.flatten():
                    all_results.append({
                        "label_id":   class_ids[i],
                        "confidence": confidences[i],
                        "box":        boxes[i],
                        "source":     engine["name"],
                    })

        # Cross-model suppression: remove hybrid detections that overlap with
        # a confirmed "person" from the global model (prevents human→animal_wild FP).
        person_boxes = [d["box"] for d in all_results
                        if d["source"] == "global" and d["label_id"] == PERSON_CLASS_ID]
        if person_boxes:
            filtered = []
            for d in all_results:
                if d["source"] == "custom":
                    suppressed = any(_iou(d["box"], pb) >= CROSS_IOU_THRESH
                                     for pb in person_boxes)
                    if suppressed:
                        continue
                filtered.append(d)
            return filtered

        return all_results
