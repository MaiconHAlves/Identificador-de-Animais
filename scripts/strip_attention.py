"""
Remove o bloco PSA (atencao) do modelo YOLOv8 para compatibilidade com OpenCV 4.5.1.

Estrutura do bloco PSA em model.10:
  b = Split_output_1                       <- entrada
  attn_out = attn(b)                       <- MatMul+Softmax: falha no OpenCV 4.5.1
  b2 = Add(b, proj_conv(attn_out))         <- m.0/Add
  b3 = Add(b2, ffn(b2))                   <- m.0/Add_1  (FFN = apenas Conv, OK)

Bypass: substituir m.0/Add por Identity(b) -> b2
  -> b2 = b  (sem atencao)
  -> FFN continua normal

Uso:
  python scripts/strip_attention.py
  python scripts/strip_attention.py models/meu_modelo_cv451.onnx
"""
import sys
import onnx
from onnx import helper, shape_inference


# --- Helpers -----------------------------------------------------------------

def build_index(graph):
    """Retorna {tensor_name: [node_name, ...]} para producao de tensores."""
    producers = {}
    for n in graph.node:
        for o in n.output:
            if o:
                producers.setdefault(o, []).append(n.name)
    return producers


def collect_upstream_names(graph, start_tensor, stop_tensors, inits):
    """Retorna set de NOMES de nos a montante de start_tensor."""
    producers = build_index(graph)
    by_name = {n.name: n for n in graph.node}
    visited = set()
    queue = [start_tensor]
    while queue:
        t = queue.pop()
        if t in stop_tensors or t in inits or not t:
            continue
        for nname in producers.get(t, []):
            if nname in visited:
                continue
            visited.add(nname)
            node = by_name[nname]
            for inp in node.input:
                if inp:
                    queue.append(inp)
    return visited


# --- Bypass do bloco de atencao ----------------------------------------------

def strip_psa_attention(graph):
    ATTN_ADD_NAME  = '/model.10/m/m.0/Add'
    PROJ_CONV_OUT  = '/model.10/m/m.0/attn/proj/conv/Conv_output_0'
    BOUNDARY_IN    = '/model.10/Split_output_1'

    by_name = {n.name: n for n in graph.node}

    if ATTN_ADD_NAME not in by_name:
        print("  Bloco PSA nao encontrado neste modelo.")
        return 0

    attn_add = by_name[ATTN_ADD_NAME]
    add_out  = attn_add.output[0]

    inits = {i.name for i in graph.initializer}
    stop  = {BOUNDARY_IN}

    names_to_remove = collect_upstream_names(graph, PROJ_CONV_OUT, stop, inits)
    names_to_remove.add(ATTN_ADD_NAME)

    print("  Nos a remover (%d):" % len(names_to_remove))
    for nm in sorted(names_to_remove):
        print("    " + nm)

    # Adicionar Identity: b -> b2
    identity = helper.make_node(
        "Identity",
        inputs=[BOUNDARY_IN],
        outputs=[add_out],
        name="/model.10/m/m.0/attn_bypass",
    )
    graph.node.append(identity)

    # Remover nos do bloco de atencao
    to_del = [n for n in graph.node if n.name in names_to_remove]
    for n in to_del:
        graph.node.remove(n)

    print("  Identity: %s -> %s" % (BOUNDARY_IN, add_out))
    print("  %d nos removidos." % len(to_del))
    return len(to_del)


# --- Ordenacao topologica ------------------------------------------------

def topo_sort(graph):
    """Reordena os nos do grafo em ordem topologica."""
    inits = {i.name for i in graph.initializer}
    graph_inputs = {i.name for i in graph.input}
    available = inits | graph_inputs

    nodes = list(graph.node)
    sorted_nodes = []
    remaining = list(nodes)

    for _ in range(len(nodes) + 1):
        if not remaining:
            break
        ready = []
        still_waiting = []
        for n in remaining:
            needed = [inp for inp in n.input if inp and inp not in available]
            if not needed:
                ready.append(n)
            else:
                still_waiting.append(n)
        if not ready:
            # ciclo ou tensores ausentes — manter ordem original dos restantes
            sorted_nodes.extend(still_waiting)
            break
        for n in ready:
            sorted_nodes.append(n)
            for o in n.output:
                if o:
                    available.add(o)
        remaining = still_waiting

    del graph.node[:]
    graph.node.extend(sorted_nodes)


# --- Corrigir axis negativo em Concat (OpenCV 4.5.1 nao suporta) -----------

def fix_negative_concat_axes(graph):
    """Converte axis=-1 para axis positivo equivalente em nos Concat."""
    fixed = 0
    # Precisamos do shape_info para descobrir o rank; usamos heuristica: rank=3 para
    # tensores do detection head (batch, features, anchors)
    for n in graph.node:
        if n.op_type != 'Concat':
            continue
        for attr in n.attribute:
            if attr.name == 'axis' and attr.i < 0:
                # Determinar rank dos inputs (assume rank 3 para detection head)
                rank = 3  # [batch, channels/features, anchors]
                new_axis = rank + attr.i  # -1 -> 2, -2 -> 1, etc.
                old = attr.i
                attr.i = new_axis
                print(f'  Concat {n.name[:50]}: axis {old} -> {new_axis}')
                fixed += 1
    return fixed


# --- Pipeline ----------------------------------------------------------------

def process(input_path):
    stem = input_path.replace("_cv451", "").rsplit(".", 1)[0]
    output_path = stem + "_cv451_noattn.onnx"

    print("\nCarregando: " + input_path)
    m = onnx.load(input_path)
    g = m.graph

    strip_psa_attention(g)
    n_fixed = fix_negative_concat_axes(g)
    print(f"  Concat axis negativos corrigidos: {n_fixed}")
    topo_sort(g)

    # Anotar shapes intermediários: OpenCV 4.5.1 lê value_info para definir ndims
    # Sem isso, Reshape 3D→4D no DFL falha em shape_utils.hpp:171
    m = shape_inference.infer_shapes(m)
    g = m.graph

    # Garantir opset 12
    del m.opset_import[:]
    m.opset_import.append(helper.make_opsetid("", 12))
    m.ir_version = 7

    try:
        onnx.checker.check_model(m)
        print("  check_model: OK")
    except Exception as e:
        print("  check_model aviso: " + str(e))

    onnx.save(m, output_path)
    print("Salvo: " + output_path)
    return output_path


if __name__ == "__main__":
    paths = sys.argv[1:] if len(sys.argv) > 1 else [
        "models/global_animal_detector_cv451.onnx",
        "models/hybrid_animal_detector_cv451.onnx",
    ]
    for p in paths:
        process(p)
