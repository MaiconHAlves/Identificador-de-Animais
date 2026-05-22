import os
import shutil
import random
import glob

def prepare_dataset():
    input_imgs = "datasets/brasil_animais"
    input_labels = "datasets/brasil_animais_labels"
    output_base = "datasets/yolo_final"
    
    # Estrutura YOLOv8
    splits = ['train', 'val']
    for s in splits:
        os.makedirs(os.path.join(output_base, "images", s), exist_ok=True)
        os.makedirs(os.path.join(output_base, "labels", s), exist_ok=True)

    species = [d for d in os.listdir(input_imgs) if os.path.isdir(os.path.join(input_imgs, d))]
    
    all_data = []
    
    for sp in species:
        images = glob.glob(os.path.join(input_imgs, sp, "*.jpg")) + glob.glob(os.path.join(input_imgs, sp, "*.jpeg"))
        for img in images:
            name = os.path.basename(img).rsplit('.', 1)[0]
            lbl = os.path.join(input_labels, sp, name + ".txt")
            if os.path.exists(lbl):
                all_data.append((img, lbl))

    print(f"[*] Total de imagens rotuladas encontradas: {len(all_data)}")
    
    # Shuffle e Split (80% train, 20% val)
    random.shuffle(all_data)
    split_idx = int(len(all_data) * 0.8)
    train_data = all_data[:split_idx]
    val_data = all_data[split_idx:]

    def copy_data(data_list, split_name):
        for img, lbl in data_list:
            img_name = os.path.basename(img)
            lbl_name = os.path.basename(lbl)
            
            # Adiciona o nome da espécie ao arquivo para evitar duplicatas
            sp_name = os.path.basename(os.path.dirname(img))
            new_img_name = f"{sp_name}_{img_name}"
            new_lbl_name = f"{sp_name}_{lbl_name}"
            
            shutil.copy(img, os.path.join(output_base, "images", split_name, new_img_name))
            shutil.copy(lbl, os.path.join(output_base, "labels", split_name, new_lbl_name))

    print("[*] Copiando arquivos para estrutura final...")
    copy_data(train_data, 'train')
    copy_data(val_data, 'val')
    
    # Criar arquivo data.yaml
    yaml_content = f"""
path: {os.path.abspath(output_base)}
train: images/train
val: images/val

names:
  0: animal_wild
  1: animal_domestic
  2: human
  3: vehicle
"""
    with open(os.path.join(output_base, "data.yaml"), 'w') as f:
        f.write(yaml_content)

if __name__ == "__main__":
    prepare_dataset()
    print("\n[V] Dataset final preparado em 'datasets/yolo_final'!")
    print("[!] Use o arquivo 'data.yaml' para iniciar o treinamento no YOLOv8.")
