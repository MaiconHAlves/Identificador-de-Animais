import cv2
import numpy as np
import onnxruntime as ort

class DetectionEngine:
    def __init__(self, model_path="yolov8n.onnx", conf_threshold=0.4, iou_threshold=0.5):
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # Configura Provedores (Prioridade para CUDA/RTX 3090)
        providers = [
            ('CUDAExecutionProvider', {
                'device_id': 0,
                'arena_extend_strategy': 'kSameAsRequested',
                'gpu_mem_limit': 2 * 1024 * 1024 * 1024, # Limite de 2GB para a Engine
                'cudnn_conv_algo_search': 'EXHAUSTIVE',
                'do_copy_in_default_stream': True,
            }),
            'CPUExecutionProvider'
        ]
        
        try:
            self.session = ort.InferenceSession(model_path, providers=providers)
            print(f"Engine iniciada com sucesso: {self.session.get_providers()[0]}")
        except Exception as e:
            print(f"Aviso: Falha ao carregar CUDA. Usando CPU. Erro: {e}")
            self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

        self.input_name = self.session.get_inputs()[0].name
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
        h, w = frame.shape[:2]
        input_tensor = self.preprocess(frame)
        
        # Inferência
        outputs = self.session.run(None, {self.input_name: input_tensor})
        
        # Pós-processamento YOLOv8 (Output: [1, 84, 8400])
        output = np.squeeze(outputs[0])
        output = output.transpose() # [8400, 84]
        
        boxes = []
        confidences = []
        class_ids = []

        for row in output:
            classes_scores = row[4:]
            max_score = np.amax(classes_scores)
            
            if max_score >= self.conf_threshold:
                class_id = np.argmax(classes_scores)
                
                # YOLOv8 boxes são [x_center, y_center, width, height]
                x, y, w_box, h_box = row[:4]
                
                # Converter para [x1, y1, w, h] para o NMS do OpenCV
                left = int((x - w_box/2) * (w / self.input_width))
                top = int((y - h_box/2) * (h / self.input_height))
                width = int(w_box * (w / self.input_width))
                height = int(h_box * (h / self.input_height))
                
                boxes.append([left, top, width, height])
                confidences.append(float(max_score))
                class_ids.append(class_id)

        # Non-Maximum Suppression (NMS)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.conf_threshold, self.iou_threshold)
        
        results = []
        if len(indices) > 0:
            for i in indices.flatten():
                results.append({
                    "label_id": class_ids[i],
                    "confidence": confidences[i],
                    "box": boxes[i] # [x, y, w, h]
                })
                
        return results

if __name__ == "__main__":
    print("Módulo de Detecção pronto.")
