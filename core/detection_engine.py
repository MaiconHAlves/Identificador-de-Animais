import cv2
import numpy as np
import onnxruntime as ort

class DetectionEngine:
    def __init__(self, model_paths=["yolo11s.onnx"], conf_threshold=0.85, iou_threshold=0.5):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        self.sessions = []
        
        # Configura Provedores (Prioridade para CUDA/RTX 3090)
        providers = [
            ('CUDAExecutionProvider', {
                'device_id': 0,
                'arena_extend_strategy': 'kSameAsRequested',
                'gpu_mem_limit': 1 * 1024 * 1024 * 1024, # 1GB por modelo
                'cudnn_conv_algo_search': 'EXHAUSTIVE',
                'do_copy_in_default_stream': True,
            }),
            'CPUExecutionProvider'
        ]
        
        for path in model_paths:
            try:
                session = ort.InferenceSession(path, providers=providers)
                print(f"Engine [{path}] iniciada: {session.get_providers()[0]}")
                self.sessions.append({
                    "session": session,
                    "input_name": session.get_inputs()[0].name,
                    "name": "custom" if "hybrid" in path.lower() or "road" in path.lower() else "global"
                })
            except Exception as e:
                print(f"Aviso: Falha ao carregar {path} em CUDA. Usando CPU. Erro: {e}")
                session = ort.InferenceSession(path, providers=['CPUExecutionProvider'])
                self.sessions.append({
                    "session": session,
                    "input_name": session.get_inputs()[0].name,
                    "name": "custom" if "hybrid" in path.lower() or "road" in path.lower() else "global"
                })

        self.input_width = 640
        self.input_height = 640

    def preprocess(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (self.input_width, self.input_height))
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1)) # HWC -> CHW
        img = np.expand_dims(img, axis=0)
        return img

    def detect(self, frame):
        h_orig, w_orig = frame.shape[:2]
        input_tensor = self.preprocess(frame)
        
        all_results = []
        
        for engine in self.sessions:
            # Inferência
            outputs = engine["session"].run(None, {engine["input_name"]: input_tensor})
            
            # Pós-processamento YOLOv8/11 (Output: [1, XX, 8400])
            output = np.squeeze(outputs[0])
            output = output.transpose() # [8400, XX]
            
            boxes = []
            confidences = []
            class_ids = []

            for row in output:
                classes_scores = row[4:]
                max_score = np.amax(classes_scores)
                
                if max_score >= self.conf_threshold:
                    class_id = np.argmax(classes_scores)
                    x, y, w_box, h_box = row[:4]
                    
                    left = int((x - w_box/2) * (w_orig / self.input_width))
                    top = int((y - h_box/2) * (h_orig / self.input_height))
                    width = int(w_box * (w_orig / self.input_width))
                    height = int(h_box * (h_orig / self.input_height))
                    
                    boxes.append([left, top, width, height])
                    confidences.append(float(max_score))
                    class_ids.append(class_id)

            indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
            
            if len(indices) > 0:
                for i in indices.flatten():
                    all_results.append({
                        "label_id": class_ids[i],
                        "confidence": confidences[i],
                        "box": boxes[i],
                        "source": engine["name"]
                    })
                    
        return all_results
