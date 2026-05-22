"""
Fix Resize nodes with empty roi input for ORT 1.25+ compatibility.
ORT 1.25 rejects Resize nodes where input[1] (roi) is "" (empty string).
Fix: inject a named empty float32 initializer as the roi tensor.
"""
import onnx
import numpy as np
from onnx import numpy_helper, TensorProto
import os
import sys


def fix_resize_roi(input_path, output_path):
    model = onnx.load(input_path)
    graph = model.graph

    # Collect existing initializer names to avoid duplicates
    init_names = {init.name for init in graph.initializer}

    roi_init_name = "__empty_roi__"
    needs_roi_init = False

    for node in graph.node:
        if node.op_type != "Resize":
            continue
        # Resize inputs: [X, roi, scales, sizes] — roi is input[1]
        if len(node.input) >= 2 and node.input[1] == "":
            node.input[1] = roi_init_name
            needs_roi_init = True

    if needs_roi_init and roi_init_name not in init_names:
        empty_roi = numpy_helper.from_array(
            np.array([], dtype=np.float32),
            name=roi_init_name,
        )
        graph.initializer.append(empty_roi)

    onnx.checker.check_model(model)
    onnx.save(model, output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    targets = [
        "global_animal_detector_nodfl.onnx",
        "hybrid_animal_detector_nodfl.onnx",
    ]
    for fname in targets:
        src = os.path.join(models_dir, fname)
        dst = src  # overwrite in-place
        if not os.path.exists(src):
            print(f"Skipping (not found): {src}")
            continue
        print(f"Fixing {fname} ...")
        fix_resize_roi(src, dst)
    print("Done.")
