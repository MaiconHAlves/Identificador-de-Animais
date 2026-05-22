import os
import shutil
import glob
import argparse

# Mapeamento Final Desejado
# 0: animal_wild
# 1: animal_domestic
# 2: human
# 3: vehicle
TARGET_CLASSES = {
    0: "animal_wild",
    1: "animal_domestic",
    2: "human",
    3: "vehicle"
}

def remap_yolo_labels(label_path, output_path, mapping_dict):
    """
    mapping_dict: {old_id: new_id}
    """
    if not os.path.exists(label_path):
        return

    with open(label_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        parts = line.strip().split()
        if not parts:
            continue
        
        old_id = int(parts[0])
        if old_id in mapping_dict:
            parts[0] = str(mapping_dict[old_id])
            new_lines.append(" ".join(parts) + "\n")
    
    if new_lines:
        with open(output_path, 'w') as f:
            f.writelines(new_lines)

def unify_dataset(source_dir, dest_dir, mapping_dict, split='train'):
    """
    source_dir: pasta raiz do dataset original (deve ter images/ e labels/)
    dest_dir: pasta raiz do dataset unificado
    """
    print(f"[*] Unificando split '{split}' de {source_dir}...")
    
    img_dest = os.path.join(dest_dir, "images", split)
    lbl_dest = os.path.join(dest_dir, "labels", split)
    os.makedirs(img_dest, exist_ok=True)
    os.makedirs(lbl_dest, exist_ok=True)

    img_exts = ['*.jpg', '*.jpeg', '*.png']
    images = []
    for ext in img_exts:
        images.extend(glob.glob(os.path.join(source_dir, "images", split, ext)))

    count = 0
    for img_path in images:
        base_name = os.path.basename(img_path)
        name_no_ext = os.path.splitext(base_name)[0]
        label_name = name_no_ext + ".txt"
        label_src = os.path.join(source_dir, "labels", split, label_name)
        
        if os.path.exists(label_src):
            # Copia imagem
            shutil.copy(img_path, os.path.join(img_dest, base_name))
            # Remapeia e salva label
            remap_yolo_labels(label_src, os.path.join(lbl_dest, label_name), mapping_dict)
            count += 1

    print(f"[V] {count} imagens processadas de {source_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unificador de Datasets YOLO para Classes de Fauna Rodoviária")
    parser.add_argument("--src", type=str, required=True, help="Pasta do dataset fonte (ex: downloads/bragan)")
    parser.add_argument("--dest", type=str, default="datasets/unificado", help="Pasta de destino")
    parser.add_argument("--map", type=str, required=True, help="Mapeamento no formato 'old1:new1,old2:new2'")
    parser.add_argument("--split", type=str, default="train", help="train ou val")
    args = parser.parse_args()

    # Parse mapping: "0:0,1:0,2:0" -> {0:0, 1:0, 2:0}
    mapping = {}
    try:
        for pair in args.map.split(","):
            old, new = pair.split(":")
            mapping[int(old)] = int(new)
    except:
        print("[!] Erro no formato do mapeamento. Use 'old:new,old:new'")
        exit(1)

    unify_dataset(args.src, args.dest, mapping, split=args.split)
