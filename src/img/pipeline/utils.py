from __future__ import annotations
def extract_edges_from_cue(cue):
    content = cue['content']
    cue_type = cue['type']
    edges = []

    if cue_type == 'obj-obj' or cue_type == 'att|obj-att|obj':
        for i in range(len(content) - 2):
            triple = tuple(content[i:i+3])
            if len(triple) == 3:
                edges.append(triple)

    elif cue_type == 'att|obj-obj':
        if len(content) >= 4:
            # skip first attribute
            edges.append((content[1], content[2], content[3]))

    elif cue_type == 'obj-att|obj':
        if len(content) >= 3:
            edges.append((content[0], content[1], content[2]))

    # att|obj 只有节点,没有边
    return edges

def which_vng_for_cues(vng_dict, trait_cues):
    """
    根据线索的节点和边信息,判断线索属于哪个 VNG

    Parameters:
    ----------
    vng_dict: dict
        VNG 的字典,key 是 VNG 的名字,value 是 VNG 的图对象
    trait_cues: list
        线索列表,每个线索是一个字典,包含 'type' 和 'content' 键
    """
    cue_mapping = []

    # 提取每个 VNG 的节点值集合 + 边集合
    vng_node_values = {}
    vng_edge_signatures = {}

    for vng_name, G in vng_dict.items():
        # 所有节点 value
        node_values = {data.get('value', '') for _, data in G.nodes(data=True)}
        # 所有边：格式是 (src_value, relation, dst_value)
        edge_signatures = set()

        for u, v, data in G.edges(data=True):
            src_val = G.nodes[u].get('value', '')
            dst_val = G.nodes[v].get('value', '')
            relation = data.get('value', '')
            if src_val and dst_val and relation:
                edge_signatures.add((src_val, relation, dst_val))

        vng_node_values[vng_name] = node_values
        vng_edge_signatures[vng_name] = edge_signatures

    for cue in trait_cues:
        content_set = set(cue['content'])

        # ----------- 边信息提取 -------------
        # 假设线索格式是 ['A', 'relation', 'B']（偶数长度,每3项是一个组合）
        edges_from_cue = extract_edges_from_cue(cue)

        best_match = None
        best_score = -1

        for vng_name in vng_dict:
            node_match = len(content_set & vng_node_values[vng_name])
            edge_match = sum(1 for edge in edges_from_cue if edge in vng_edge_signatures[vng_name])
            total_score = node_match + 2 * edge_match  # 权重：边更重要

            if total_score > best_score:
                best_match = vng_name
                best_score = total_score

        if best_match:
            cue_mapping.append(best_match)

    return list(dict.fromkeys(cue_mapping))


def identify_cue_type(cue):
    cue_type = cue['type']
    content = cue['content']

    cue_nodes = []
    cue_edges = []
    mapping = {
        'obj-obj': ([0, 2], [1]),
        'att|obj-att|obj': ([1, 4], [2]),
        'att|obj-obj': ([1, 3], [2]),
        'obj-att|obj': ([0, 3], [1]),
        'att|obj': ([1], []),
    }

    if cue_type in mapping:
        node_indices, edge_indices = mapping[cue_type]
        cue_nodes = [content[i] for i in node_indices]
        cue_edges = [content[i] for i in edge_indices]

    return {'nodes': cue_nodes, 'edges': cue_edges}

def find_key_in_result(result: dict, target_key: str) -> dict:
    """
    在嵌套字典中查找特定键（不区分大小写）

    参数:
        result: 嵌套字典
        target_key: 要查找的键名

    返回:
        包含目标键的字典
    """
    current_dict = result
    while True:
        # Check for exact match
        if target_key in current_dict:
            return {target_key: current_dict[target_key]}

        # Check for case-insensitive match
        lower_target_key = target_key.lower()
        keys_lower = {k.lower(): k for k in current_dict.keys()}
        if lower_target_key in keys_lower:
            original_key = keys_lower[lower_target_key]
            return {target_key: current_dict[original_key]}

        # Check if we can go deeper
        dict_values = [v for v in current_dict.values() if isinstance(v, dict)]
        if not dict_values:
            raise ValueError(f'无法找到{target_key}键, 原始输出: {result}')

        current_dict = dict_values[0]

def _replace_pronouns(text, name='Ye'):
        """Replace the pronouns in the text and you can choose to extract the sentences"""
        if 'you' in text.lower() or 'your' in text.lower():
            text = (
                text
                    .replace(f'your', f"{name}'s")
                    .replace(f'Your', f"{name}'s")
                    .replace(f'you', f'{name}')
                    .replace(f'You', f'{name}')
                    .replace(f'are', 'is')
                    .replace(f'Are', 'Is')
                    .replace(f"'re", f' is')
                    .replace(f"'re", f' is')
            )
            if not text.endswith('.'):
                text = text + '.'
        if '你' in text or '您' in text:
            text = (
                text
                    .replace(f'您', f"{name}")
                    .replace(f'你', f'{name}')
            )
            if not text.endswith('。'):
                text = text + '。'
        return text
