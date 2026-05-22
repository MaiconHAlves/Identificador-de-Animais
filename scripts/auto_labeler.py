import os
import cv2
from ultralytics import YOLO
import glob
from tqdm import tqdm

# Configuração: Mapeamento de classes COCO para o seu formato
# No COCO: 14: bird, 15: cat, 16: dog, 17: horse, 18: sheep, 19: cow, etc.
# Queremos mapear qualquer detecção de animal nas pastas "wild" para a classe 0 (animal_wild)
ANIMAL_COCO_CLASSES = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23] 
HUMAN_COCO_CLASSES = [0]
VEHICLE_COCO_CLASSES = [1, 2, 3, 5, 7] # bicycle, car, motorcycle, bus, truck

def auto_label():
    print("[*] Carregando modelo YOLOv8n para auto-rotulagem...")
    model = YOLO('yolov8n.pt')
    
    input_base = "datasets/brasil_animais"
    output_base = "datasets/brasil_animais_labels"
    os.makedirs(output_base, exist_ok=True)

    species_folders = [f for f in os.listdir(input_base) if os.path.isdir(os.path.join(input_base, f))]

    for species in species_folders:
        print(f"\n[*] Processando espécie: {species}")
        img_dir = os.path.join(input_base, species)
        lbl_dir = os.path.join(output_base, species)
        os.makedirs(lbl_dir, exist_ok=True)

        images = glob.glob(os.path.join(img_dir, "*.jpg")) + glob.glob(os.path.join(img_dir, "*.jpeg"))
        
        for img_path in tqdm(images, desc=species):
            results = model(img_path, verbose=False)[0]
            
            label_filename = os.path.basename(img_path).rsplit('.', 1)[0] + ".txt"
            label_path = os.path.join(lbl_dir, label_filename)

            with open(label_path, 'w') as f:
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    if conf < 0.25: # Filtro de confiança
                        continue

                    # Lógica de Remapeamento
                    target_id = None
                    if cls_id in ANIMAL_COCO_CLASSES:
                        target_id = 0 # animal_wild (já que estamos nas pastas de animais silvestres)
                    elif cls_id in HUMAN_COCO_CLASSES:
                        target_id = 2 # human
                    elif cls_id in VEHICLE_COCO_CLASSES:
                        target_id = 3 # vehicle
                    
                    if target_id is not None:
                        # Formato YOLO: class x_center y_center width height (normalizado)
                        xywh = box.xywhn[0].tolist()
                        f.write(f"{target_id} {' '.join(map(str, xywh))}\n")

if __name__ == "__main__":
    auto_label()
    print("\n[V] Auto-rotulagem concluída! Verifique 'datasets/brasil_animais_labels'")
