"""
Converte modelos ONNX exportados com opset >= 13 para opset 12,
compatível com OpenCV 4.5.x DNN.

Correções aplicadas:
  - Split: move split sizes de tensor input para atributo (opset 13 → 12)
  - Reshape: remove atributo 'allowzero' (adicionado no opset 14)

Uso:
  python scripts/fix_onnx_opset.py models/meu_modelo.onnx
  # gera: models/meu_modelo_cv451.onnx
"""
import sys
import onnx
from onnx import numpy_helper, helper


def fix_for_opencv451(input_path: str, output_path: str | None = None) -> str:
    if output_path is None:
        stem = input_path.rsplit(".", 1)[0]
        output_path = stem + "_cv451.onnx"

    m = onnx.load(input_path)
    inits = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    split_init_names = set()

    for node in m.graph.node:
        if node.op_type == "Split" and len(node.input) > 1:
            split_name = node.input[1]
            sizes = inits[split_name].tolist()
            split_init_names.add(split_name)
            del node.input[1]
            if "split" not in {a.name for a in node.attribute}:
                node.attribute.append(helper.make_attribute("split", sizes))

        if node.op_type == "Reshape":
            to_remove = [a for a in node.attribute if a.name == "allowzero"]
            for a in to_remove:
                node.attribute.remove(a)

    new_inits = [i for i in m.graph.initializer if i.name not in split_init_names]
    del m.graph.initializer[:]
    m.graph.initializer.extend(new_inits)

    del m.opset_import[:]
    m.opset_import.append(helper.make_opsetid("", 12))
    m.ir_version = 7

    onnx.save(m, output_path)
    print(f"Salvo: {output_path}")
    return output_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "models/global_animal_detector.onnx"
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    fix_for_opencv451(src, dst)
