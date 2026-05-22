"""
Fix Resize nodes in _sim_fixed.onnx models.

OpenCV 4.5.1 parses Resize attributes as strings per ONNX spec (opset 11+).
When mode and coordinate_transformation_mode are stored as integers (0, 0),
OpenCV cannot compute the output shape, causing shape_utils.hpp:171 assertion.

This script:
1. Converts Resize integer attrs to proper strings
2. Re-runs shape inference
3. Saves as _sim_fixed2.onnx

Usage:
  python scripts/fix_resize_attrs.py
  python scripts/fix_resize_attrs.py models/my_model_sim_fixed.onnx
"""
import sys
import onnx
from onnx import helper, shape_inference, TensorProto

RESIZE_INT_TO_STR_MODE = {
    0: "nearest",
    1: "linear",
    2: "cubic",
}

RESIZE_INT_TO_STR_COORD = {
    0: "asymmetric",
    1: "align_corners",
    2: "half_pixel",
    3: "pytorch_half_pixel",
    4: "tf_crop_and_resize",
    5: "tf_half_pixel_for_nn",
}

RESIZE_INT_TO_STR_NEAREST = {
    0: "round_prefer_floor",
    1: "round_prefer_ceil",
    2: "floor",
    3: "ceil",
}


def fix_resize_nodes(graph):
    fixed = 0
    for node in graph.node:
        if node.op_type != "Resize":
            continue
        for attr in node.attribute:
            if attr.name == "mode":
                if attr.type == onnx.AttributeProto.INT:
                    str_val = RESIZE_INT_TO_STR_MODE.get(attr.i, "nearest")
                    print(f"  Resize {node.name}: mode {attr.i} -> '{str_val}'")
                    attr.type = onnx.AttributeProto.STRING
                    attr.s = str_val.encode()
                    attr.ClearField("i")
                    fixed += 1
            elif attr.name == "coordinate_transformation_mode":
                if attr.type == onnx.AttributeProto.INT:
                    str_val = RESIZE_INT_TO_STR_COORD.get(attr.i, "asymmetric")
                    print(f"  Resize {node.name}: coordinate_transformation_mode {attr.i} -> '{str_val}'")
                    attr.type = onnx.AttributeProto.STRING
                    attr.s = str_val.encode()
                    attr.ClearField("i")
                    fixed += 1
            elif attr.name == "nearest_mode":
                if attr.type == onnx.AttributeProto.INT:
                    str_val = RESIZE_INT_TO_STR_NEAREST.get(attr.i, "round_prefer_floor")
                    print(f"  Resize {node.name}: nearest_mode {attr.i} -> '{str_val}'")
                    attr.type = onnx.AttributeProto.STRING
                    attr.s = str_val.encode()
                    attr.ClearField("i")
                    fixed += 1
    return fixed


def inspect_resize(graph):
    """Print all Resize node attributes for inspection."""
    for node in graph.node:
        if node.op_type != "Resize":
            continue
        print(f"  Resize node: {node.name}")
        for attr in node.attribute:
            if attr.type == onnx.AttributeProto.STRING:
                print(f"    {attr.name} = '{attr.s.decode()}' (string)")
            elif attr.type == onnx.AttributeProto.INT:
                print(f"    {attr.name} = {attr.i} (INT — needs fix)")
            elif attr.type == onnx.AttributeProto.FLOAT:
                print(f"    {attr.name} = {attr.f} (float)")
            elif attr.type == onnx.AttributeProto.INTS:
                print(f"    {attr.name} = {list(attr.ints)} (ints)")
            elif attr.type == onnx.AttributeProto.FLOATS:
                print(f"    {attr.name} = {list(attr.floats)} (floats)")


def process(input_path):
    stem = input_path.rsplit(".", 1)[0]
    # Replace _sim_fixed with _sim_fixed2, or append _fixed2
    if "_sim_fixed" in stem:
        output_path = stem.replace("_sim_fixed", "_sim_fixed2") + ".onnx"
    else:
        output_path = stem + "_fixed2.onnx"

    print(f"\nLoading: {input_path}")
    m = onnx.load(input_path)
    g = m.graph

    print("Before fix:")
    inspect_resize(g)

    n_fixed = fix_resize_nodes(g)
    print(f"  Fixed {n_fixed} Resize attributes")

    print("After fix:")
    inspect_resize(g)

    # Re-run shape inference with corrected attributes
    m = shape_inference.infer_shapes(m)
    g = m.graph

    # Force opset 12
    del m.opset_import[:]
    m.opset_import.append(helper.make_opsetid("", 12))
    m.ir_version = 7

    try:
        onnx.checker.check_model(m)
        print("  check_model: OK")
    except Exception as e:
        print(f"  check_model warning: {e}")

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
