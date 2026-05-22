"""
Strip DFL post-processing from YOLOv8 ONNX for OpenCV 4.5.1 compatibility.

OpenCV 4.5.1 DNN fails on the DFL head: Transpose+Softmax+Conv+Slice chain
causes shape_utils.hpp:171 assertion failures.

This script creates a simplified model that outputs:
  - output_boxes: [1, 64, 8400]  raw DFL box features (4 coords × 16 bins × 8400 anchors)
  - output_scores: [1, 80, 8400] class scores after Sigmoid

Python-side DFL decoding in detection_engine.py handles the rest.

Usage:
  python scripts/strip_dfl_head.py
  python scripts/strip_dfl_head.py models/my_sim_fixed.onnx
"""
import sys
import onnx
import numpy as np
from onnx import helper, shape_inference, numpy_helper, TensorProto


# Nodes to keep: everything up to and including model.23/Concat and model.23/Sigmoid
# All nodes in the DFL block and post-processing are removed
DFL_STRIP_PREFIXES = [
    "/model.23/dfl/",
    "/model.23/Slice",
    "/model.23/Sub",
    "/model.23/Add_1",
    "/model.23/Add_2",
    "/model.23/Sub_1",
    "/model.23/Div",
    "/model.23/Concat_2",
    "/model.23/Concat_3",
    "/model.23/Mul_2",
    "/model.23/Constant_12",
    "/model.23/Constant_13",
    "/model.23/Constant_14",
    "/model.23/Constant_15",
    "/model.23/Constant_6",
    "/model.23/Constant_7",
    "/model.23/Mul_output_0",  # not a node but initializer
    "/model.23/Mul_1_output_0",
]


def should_strip(node_name):
    for prefix in DFL_STRIP_PREFIXES:
        if node_name.startswith(prefix):
            return True
    return False


def fix_negative_concat_axes(graph):
    fixed = 0
    for n in graph.node:
        if n.op_type != 'Concat':
            continue
        for attr in n.attribute:
            if attr.name == 'axis' and attr.i < 0:
                rank = 3
                new_axis = rank + attr.i
                attr.i = new_axis
                fixed += 1
    return fixed


def process(input_path):
    stem = input_path.rsplit(".", 1)[0]
    # Replace _sim_fixed with _nodfl, or append _nodfl
    if "_sim_fixed" in stem:
        output_path = stem.replace("_sim_fixed", "_nodfl") + ".onnx"
    elif "_sim" in stem:
        output_path = stem.replace("_sim", "_nodfl") + ".onnx"
    else:
        output_path = stem + "_nodfl.onnx"

    print(f"\nLoading: {input_path}")
    m = onnx.load(input_path)
    g = m.graph

    # Identify nodes to remove
    nodes_to_remove = []
    for n in g.node:
        if should_strip(n.name):
            nodes_to_remove.append(n)

    removed_names = {n.name for n in nodes_to_remove}
    print(f"Removing {len(nodes_to_remove)} nodes:")
    for n in nodes_to_remove:
        print(f"  {n.op_type}: {n.name[:60]}")

    for n in nodes_to_remove:
        g.node.remove(n)

    # Remove initializers only used by stripped nodes
    # Keep all others (model weights etc.)
    # Find which initializers are still referenced
    used_inits = set()
    for n in g.node:
        for inp in n.input:
            if inp:
                used_inits.add(inp)
    # Also keep initializers referenced by graph outputs
    for o in g.output:
        used_inits.add(o.name)

    original_init_count = len(g.initializer)
    new_inits = [i for i in g.initializer if i.name in used_inits]
    del g.initializer[:]
    g.initializer.extend(new_inits)
    print(f"Initializers: {original_init_count} -> {len(new_inits)}")

    # Fix negative Concat axes
    n_concat_fixed = fix_negative_concat_axes(g)
    if n_concat_fixed:
        print(f"Fixed {n_concat_fixed} negative Concat axes")

    # Set new graph outputs
    # Find actual tensor names for our two outputs
    boxes_tensor = "/model.23/Concat_output_0"
    scores_tensor = "/model.23/Sigmoid_output_0"

    # Verify these tensors are produced by remaining nodes
    produced = set()
    for n in g.node:
        for o in n.output:
            if o:
                produced.add(o)
    for init in g.initializer:
        produced.add(init.name)

    assert boxes_tensor in produced, f"boxes tensor {boxes_tensor} not found in remaining graph"
    assert scores_tensor in produced, f"scores tensor {scores_tensor} not found in remaining graph"

    # Build new output value infos
    def make_output(name, shape):
        tensor_type = helper.make_tensor_type_proto(TensorProto.FLOAT, shape)
        return helper.make_value_info(name, tensor_type)

    del g.output[:]
    g.output.append(make_output(boxes_tensor, [1, 64, 8400]))
    g.output.append(make_output(scores_tensor, [1, 80, 8400]))

    # Force opset 12
    del m.opset_import[:]
    m.opset_import.append(helper.make_opsetid("", 12))
    m.ir_version = 7

    # Shape inference to populate value_info
    m = shape_inference.infer_shapes(m)

    try:
        onnx.checker.check_model(m)
        print("check_model: OK")
    except Exception as e:
        print(f"check_model warning: {e}")

    onnx.save(m, output_path)
    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else [
        "models/global_animal_detector_sim_fixed.onnx",
        "models/hybrid_animal_detector_sim_fixed.onnx",
    ]
    for p in paths:
        process(p)
