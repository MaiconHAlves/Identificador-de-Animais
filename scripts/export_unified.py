"""
Exporta o modelo treinado para ONNX + strip DFL head para Android (OpenCV 4.5.1).

Uso:
  py -3.12 scripts/export_unified.py --weights training/runs/unified_v1/weights/best.pt
"""
import argparse
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def export_onnx(weights: Path) -> Path:
    from ultralytics import YOLO
    model = YOLO(str(weights))
    model.export(format="onnx", imgsz=640, opset=12, simplify=True, dynamic=False)
    onnx_path = weights.with_suffix(".onnx")
    print(f"ONNX exportado: {onnx_path}")
    return onnx_path


def strip_and_fix(onnx_path: Path, out_path: Path):
    import onnx
    import numpy as np
    from onnx import numpy_helper

    model = onnx.load(str(onnx_path))
    graph = model.graph

    # 1. Fix Resize roi empty input (ORT 1.25+ compatibility)
    roi_name = "__empty_roi__"
    needs_roi = False
    for node in graph.node:
        if node.op_type == "Resize" and len(node.input) >= 2 and node.input[1] == "":
            node.input[1] = roi_name
            needs_roi = True
    if needs_roi:
        existing = {i.name for i in graph.initializer}
        if roi_name not in existing:
            graph.initializer.append(
                numpy_helper.from_array(np.array([], dtype=np.float32), name=roi_name)
            )

    # 2. Strip DFL head (nodes that cause shape_utils.hpp:171 on OpenCV 4.5.1)
    DFL_PREFIXES = (
        "/model.22/dfl/", "/model.23/dfl/",
        "/model.22/Shape", "/model.23/Shape",
        "/model.22/Gather", "/model.23/Gather",
        "/model.22/Slice", "/model.23/Slice",    # matches Slice + Slice_1
        "/model.22/Add",  "/model.23/Add",       # matches Add + Add_1 + Add_2
        "/model.22/Sub",  "/model.23/Sub",       # matches Sub + Sub_1
        "/model.22/Div",  "/model.23/Div",       # matches Div + Div_1
        "/model.22/Mul",  "/model.23/Mul",       # matches Mul + Mul_1 + Mul_2
        "/model.22/Concat_2", "/model.23/Concat_2",
        "/model.22/Concat_3", "/model.23/Concat_3",
    )

    nodes_to_keep = []
    removed = 0
    for node in graph.node:
        if any(node.name.startswith(p) for p in DFL_PREFIXES):
            removed += 1
        else:
            nodes_to_keep.append(node)
    print(f"Nós DFL removidos: {removed}")

    del graph.node[:]
    graph.node.extend(nodes_to_keep)

    # 3. Redirecionar outputs para pré-DFL (raw boxes + sigmoid scores)
    # Tenta prefixo /model.23 e /model.22 (YOLOv8 vs versões antigas)
    raw_box_candidates  = ["/model.23/Concat_output_0", "/model.22/Concat_output_0"]
    raw_score_candidates= ["/model.23/Sigmoid_output_0", "/model.22/Sigmoid_output_0"]

    all_outputs = {vi.name for vi in graph.value_info}
    all_outputs.update(i.name for i in graph.initializer)
    all_outputs.update(n.output[0] for n in graph.node if n.output)

    raw_box  = next((c for c in raw_box_candidates  if c in all_outputs), None)
    raw_score= next((c for c in raw_score_candidates if c in all_outputs), None)

    if not raw_box or not raw_score:
        print(f"AVISO: outputs pré-DFL não encontrados automaticamente.")
        print(f"  Candidatos boxes:  {raw_box_candidates}")
        print(f"  Candidatos scores: {raw_score_candidates}")
        print("  Exportando sem strip DFL.")
        onnx.save(model, str(out_path))
        return

    del graph.output[:]
    def _make_output(name):
        from onnx import helper, TensorProto
        return helper.make_tensor_value_info(name, TensorProto.FLOAT, None)
    graph.output.extend([_make_output(raw_box), _make_output(raw_score)])

    try:
        onnx.checker.check_model(model)
    except Exception as e:
        print(f"  (checker warning ignorado: {e})")

    # Shape inference — popula info de shape nos value_info para cv2.dnn 4.13+
    from onnx import shape_inference as _si
    model = _si.infer_shapes(model)

    onnx.save(model, str(out_path))
    print(f"Modelo Android salvo: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="training/runs/unified_v1/weights/best.pt")
    parser.add_argument("--out", default="models/unified_animal_detector_nodfl.onnx",
                        help="Caminho do ONNX final (após strip DFL). Default: models/unified_animal_detector_nodfl.onnx")
    args = parser.parse_args()

    weights = Path(args.weights)
    if not weights.exists():
        print(f"[ERRO] Weights não encontrado: {weights}")
        sys.exit(1)

    onnx_path = export_onnx(weights)

    out_nodfl = Path(args.out)
    out_nodfl.parent.mkdir(parents=True, exist_ok=True)
    strip_and_fix(onnx_path, out_nodfl)
    print(f"\nPronto para Android: {out_nodfl}")
    print("Atualize mobile/main.py com o novo modelo.")


if __name__ == "__main__":
    main()
