import cv2
import numpy as np


class DetectionEngine:
    def __init__(self, model_paths=["yolov8n.onnx"], conf_threshold=0.85, iou_threshold=0.5):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.input_width = 640
        self.input_height = 640
        self.nets = []

        for path in model_paths:
            try:
                net = cv2.dnn.readNetFromONNX(path)
                try:
                    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    print(f"Engine [{path}] carregada (CUDA)")
                except Exception:
                    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
                    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    print(f"Engine [{path}] carregada (CPU)")
                self.nets.append({
                    "net": net,
                    "name": "custom" if "hybrid" in path.lower() or "road" in path.lower() else "global",
                })
            except Exception as e:
                print(f"Aviso: falha ao carregar {path}: {e}")

    def detect(self, frame):
        h_orig, w_orig = frame.shape[:2]
        all_results = []

        for engine in self.nets:
            blob = cv2.dnn.blobFromImage(
                frame, 1 / 255.0, (self.input_width, self.input_height),
                swapRB=True, crop=False,
            )
            engine["net"].setInput(blob)
            output = np.squeeze(engine["net"].forward()).transpose()  # [8400, N]

            boxes, confidences, class_ids = [], [], []
            for row in output:
                classes_scores = row[4:]
                max_score = float(np.amax(classes_scores))
                if max_score >= self.conf_threshold:
                    class_id = int(np.argmax(classes_scores))
                    x, y, w_box, h_box = row[:4]
                    left   = int((x - w_box / 2) * w_orig / self.input_width)
                    top    = int((y - h_box / 2) * h_orig / self.input_height)
                    width  = int(w_box * w_orig / self.input_width)
                    height = int(h_box * h_orig / self.input_height)
                    boxes.append([left, top, width, height])
                    confidences.append(max_score)
                    class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
            if len(indices) > 0:
                for i in indices.flatten():
                    all_results.append({
                        "label_id": class_ids[i],
                        "confidence": confidences[i],
                        "box": boxes[i],
                        "source": engine["name"],
                    })

        return all_results
