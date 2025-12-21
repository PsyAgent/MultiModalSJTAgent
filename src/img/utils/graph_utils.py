from __future__ import annotations

import networkx as nx
from wasabi import msg


def print_G(G):
    """
    Print the graph structure in a readable format.
    :param G: The graph object containing nodes and edges.
    """
    print(G)
    msg.info('\nNodes:')
    for node, data in G.nodes(data=True):
        print(node, data)

    msg.info('\nEdges:')
    for u, v, data in G.edges(data=True):
        print(u, '->', v, data)


def build_G(scene_graph_dict):
    """
    根据给定的字典数据构建 NetworkX DiGraph

    :param scene_graph_dict: 字典格式的数据，包含 "nodes" 和 "edges" 两个键，
                             "nodes" 为 [node_id, node_attrs] 的列表，
                             "edges" 为 [source, target, edge_attrs] 的列表。
    :return: 构建好的 nx.DiGraph 对象
    """
    G = nx.DiGraph()

    # 添加节点
    for node_entry in scene_graph_dict.get('nodes', []):
        node_id, node_attrs = node_entry
        G.add_node(node_id, **node_attrs)

    # 添加边
    for edge_entry in scene_graph_dict.get('edges', []):
        src, dst, edge_attrs = edge_entry
        G.add_edge(src, dst, **edge_attrs)

    return G

def dic_G(G):
    graph_dict = {'nodes': [],'edges': []}

    for node, data in G.nodes(data=True):
        graph_dict['nodes'].append([node, data])

    for source, target, data in G.edges(data=True):
        graph_dict['edges'].append([source, target, data])

    return graph_dict


def get_node_id(G, value):
    """
    在图 G 中查找具有指定 value 的节点, 返回该节点的 id.

    :param G: nx.DiGraph 对象
    :param target_value: 要查找的节点 value
    :return: 匹配节点的 id, 如果找不到则返回 None
    """
    found = False
    for node, data in G.nodes(data=True):
        val = data.get('value')
        if val == value:
            return node
    if not found:
        msg.warn(f'No node found with value: {value}')
    return None


def get_edge_id(G, value):
    """
    在图 G 中查找具有指定 value 的边, 返回该边的 id.

    :param G: nx.DiGraph 对象
    :param target_value: 要查找的边 value
    :return: 匹配边的 id (如果未设置则返回 (u, v)), 如果找不到则返回 None
    """
    found = False
    for u, v, data in G.edges(data=True):
        if data.get('value') == value:
            return data.get('id', (u, v))
    if not found:
        msg.warn(f'No edge found with value: {value}')
    return None

def find_node_by_value(G, value, node_type):
    """
    在图 G 中查找类型为 node_type 且其 'value' 属性等于 value 的节点，返回节点 id（若有多个则返回第一个）
    """
    for n, data in G.nodes(data=True):
        if data.get('type') == node_type and data.get('value') == value:
            return n
    return None

def extract_knowledge(G, cue_type):
    """
    根据 cue_type 从图 G 中提取对应的知识，返回一个列表，每个元素为一个 tuple，其元素为节点和边的 value。
    可选的 cue_type 有：
      'att|obj', 'obj-obj', 'att|obj-obj', 'obj-att|obj', 'att|obj-att|obj'
    """
    knowledge = []

    if cue_type == 'att|obj':
        # 属性边: 输出 (属性节点value, 对象节点value)
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'attribute_edge':
                knowledge.append((G.nodes[u].get('value'), G.nodes[v].get('value')))

    elif cue_type == 'obj-obj':
        # 对象间关系: 输出 (起始对象value, 关系value, 目标对象value)
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'relation_edge' \
               and G.nodes[u].get('type') == 'object_node' \
               and G.nodes[v].get('type') == 'object_node':
                knowledge.append((G.nodes[u].get('value'), data.get('value'), G.nodes[v].get('value')))

    elif cue_type == 'att|obj-obj':
        # 属性边后接关系边: 输出 (属性节点value, 对象节点value, 关系value, 目标对象value)
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'attribute_edge':
                # u: attribute节点，v: 对象节点
                for _, target, rel_data in G.out_edges(v, data=True):
                    if rel_data.get('type') == 'relation_edge' and G.nodes[target].get('type') == 'object_node':
                        knowledge.append((
                            G.nodes[u].get('value'),
                            G.nodes[v].get('value'),
                            rel_data.get('value'),
                            G.nodes[target].get('value'),
                        ))

    elif cue_type == 'obj-att|obj':
        # 对象关系后目标对象存在属性边进入: 输出 (起始对象value, 关系value, 目标对象value, 属性节点value)
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'relation_edge' \
               and G.nodes[u].get('type') == 'object_node' \
               and G.nodes[v].get('type') == 'object_node':
                # 检查目标对象 v 是否存在进入的属性边
                for att, _ in G.in_edges(v):
                    if G.edges[att, v].get('type') == 'attribute_edge':
                        knowledge.append((
                            G.nodes[u].get('value'),
                            data.get('value'),
                            G.nodes[att].get('value'),
                            G.nodes[v].get('value'),
                        ))

    elif cue_type == 'att|obj-att|obj':
        # 属性边 -> 对象 -> 对象关系 -> 属性边 -> 对象
        # 输出 (第一个属性节点value, 第一个对象value, 关系value, 第二个对象value, 第二个属性节点value)
        for u, v, data in G.edges(data=True):
            if data.get('type') == 'attribute_edge':  # u->v
                for _, target, rel_data in G.out_edges(v, data=True):
                    if rel_data.get('type') == 'relation_edge' and G.nodes[target].get('type') == 'object_node':
                        for att2, _ in G.in_edges(target):
                            if G.edges[att2, target].get('type') == 'attribute_edge':
                                knowledge.append((
                                    G.nodes[u].get('value'),
                                    G.nodes[v].get('value'),
                                    rel_data.get('value'),
                                    G.nodes[att2].get('value'),
                                    G.nodes[target].get('value'),
                                ))
    else:
        raise ValueError("cue_type 必须在 ['att|obj', 'obj-obj', 'att|obj-obj', 'obj-att|obj', 'att|obj-att|obj'] 中")

    return knowledge

def map_knowledge(G, knowledge, cue_type):
    """
    根据输入的 knowledge（由 extract_knowledge 得到的 value tuple）以及 cue_type，
    在图 G 中查找对应的节点（或边）id，并返回一个 tuple 作为映射结果。

    映射规则：
      - att|obj: (att_node_id, object_node_id)
      - obj-obj: (src_obj_id, (src_obj_id, tgt_obj_id), tgt_obj_id)
      - att|obj-obj: (att_node_id, obj_node_id, (obj_node_id, target_obj_id), target_obj_id)
      - obj-att|obj: (src_obj_id, (src_obj_id, tgt_obj_id), tgt_obj_id, att_node_id)
      - att|obj-att|obj: (att_node_id1, obj_node_id1, (obj_node_id1, obj_node_id2), obj_node_id2, att_node_id2)

    例如，对于输入：
      (G, ('attractive', 'woman', 'looks at', 'Ye'), 'att|obj-obj')
    应输出：
      ('attribute|3|1', 'object_3', ('object_3', 'object_1'), 'object_1')
    """
    if cue_type == 'att|obj':
        att_val, obj_val = knowledge
        att_id = find_node_by_value(G, att_val, 'attribute_node')
        obj_id = find_node_by_value(G, obj_val, 'object_node')
        return (att_id, obj_id)

    elif cue_type == 'obj-obj':
        src_val, rel_val, tgt_val = knowledge
        src_id = find_node_by_value(G, src_val, 'object_node')
        tgt_id = find_node_by_value(G, tgt_val, 'object_node')
        if src_id is None or tgt_id is None:
            return None
        # 检查从 src_id 到 tgt_id 是否存在关系边且关系 value 匹配
        for _, v, data in G.out_edges(src_id, data=True):
            if v == tgt_id and data.get('type') == 'relation_edge' and data.get('value') == rel_val:
                return (src_id, (src_id, tgt_id), tgt_id)
        return None

    elif cue_type == 'att|obj-obj':
        # knowledge: (att_val, obj_val, rel_val, tgt_val)
        att_val, obj_val, rel_val, tgt_val = knowledge
        att_id = find_node_by_value(G, att_val, 'attribute_node')
        obj_id = find_node_by_value(G, obj_val, 'object_node')
        tgt_id = find_node_by_value(G, tgt_val, 'object_node')
        if obj_id is None or tgt_id is None:
            return None
        for _, v, data in G.out_edges(obj_id, data=True):
            if v == tgt_id and data.get('type') == 'relation_edge' and data.get('value') == rel_val:
                return (att_id, obj_id, (obj_id, tgt_id), tgt_id)
        return None

    elif cue_type == 'obj-att|obj':
        # knowledge: (src_val, rel_val, att_val, tgt_val)
        src_val, rel_val, att_val, tgt_val = knowledge
        src_id = find_node_by_value(G, src_val, 'object_node')
        tgt_id = find_node_by_value(G, tgt_val, 'object_node')
        if src_id is None or tgt_id is None:
            return None
        # 首先检查 src 到 tgt 的关系边是否存在且匹配
        relation_found = False
        for _, v, data in G.out_edges(src_id, data=True):
            if v == tgt_id and data.get('type') == 'relation_edge' and data.get('value') == rel_val:
                relation_found = True
                break
        if not relation_found:
            return None
        # 检查 tgt_id 的入边，寻找属性节点值为 att_val 且边类型为 attribute_edge
        for u, _ in G.in_edges(tgt_id):
            if G.nodes[u].get('type') == 'attribute_node' and G.nodes[u].get('value') == att_val:
                if G.edges[u, tgt_id].get('type') == 'attribute_edge':
                    return (src_id, (src_id, tgt_id), u, tgt_id)
        return None

    elif cue_type == 'att|obj-att|obj':
        # knowledge: (att_val1, obj_val1, rel_val, att_val2, obj_val2)
        att_val1, obj_val1, rel_val, att_val2, obj_val2 = knowledge
        att_id1 = find_node_by_value(G, att_val1, 'attribute_node')
        obj_id1 = find_node_by_value(G, obj_val1, 'object_node')
        obj_id2 = find_node_by_value(G, obj_val2, 'object_node')
        att_id2 = find_node_by_value(G, att_val2, 'attribute_node')
        if obj_id1 is None or obj_id2 is None:
            return None
        # 检查 obj_id1 到 obj_id2 的关系边
        relation_found = False
        for _, v, data in G.out_edges(obj_id1, data=True):
            if v == obj_id2 and data.get('type') == 'relation_edge' and data.get('value') == rel_val:
                relation_found = True
                break
        if not relation_found:
            return None
        # 检查 obj_id2 的入边，寻找属性节点值为 att_val2 且边类型为 attribute_edge
        for u, _ in G.in_edges(obj_id2):
            if G.nodes[u].get('type') == 'attribute_node' and G.nodes[u].get('value') == att_val2:
                if G.edges[u, obj_id2].get('type') == 'attribute_edge':
                    return (att_id1, obj_id1, (obj_id1, obj_id2), att_id2, obj_id2)
        return None

    else:
        raise ValueError("cue_type 必须在 ['att|obj', 'obj-obj', 'att|obj-obj', 'obj-att|obj', 'att|obj-att|obj'] 中")


def entry_build_graph(entry_list):
    """
    根据 entry_list（包含 type 和 content 的字典列表）构建一个新的有向图 G。

    :param entry_list: [{'type': ..., 'content': [...]}, ...]
    :return: NetworkX DiGraph
    """
    G = nx.DiGraph()

    for item in entry_list:
        rel_type = item.get('type')
        content = item.get('content', [])

        if rel_type == 'att|obj' and len(content) == 2:
            attr, obj = content
            attr_id = f'attribute|auto|{attr}'
            obj_id = f'object|auto|{obj}'
            G.add_node(attr_id, type='attribute_node', value=attr)
            G.add_node(obj_id, type='object_node', value=obj)
            G.add_edge(attr_id, obj_id, type='attribute_edge')

        elif rel_type == 'obj-obj' and len(content) == 3:
            src, rel, tgt = content
            src_id = f'object|auto|{src}'
            tgt_id = f'object|auto|{tgt}'
            G.add_node(src_id, type='object_node', value=src)
            G.add_node(tgt_id, type='object_node', value=tgt)
            G.add_edge(src_id, tgt_id, type='relation_edge', value=rel)

        elif rel_type == 'att|obj-obj' and len(content) == 4:
            attr, src, rel, tgt = content
            attr_id = f'attribute|auto|{attr}'
            src_id = f'object|auto|{src}'
            tgt_id = f'object|auto|{tgt}'
            G.add_node(attr_id, type='attribute_node', value=attr)
            G.add_node(src_id, type='object_node', value=src)
            G.add_node(tgt_id, type='object_node', value=tgt)
            G.add_edge(attr_id, src_id, type='attribute_edge')
            G.add_edge(src_id, tgt_id, type='relation_edge', value=rel)

        elif rel_type == 'obj-att|obj' and len(content) == 4:
            src, rel, attr, tgt = content
            src_id = f'object|auto|{src}'
            tgt_id = f'object|auto|{tgt}'
            attr_id = f'attribute|auto|{attr}'
            G.add_node(src_id, type='object_node', value=src)
            G.add_node(attr_id, type='attribute_node', value=attr)
            G.add_node(tgt_id, type='object_node', value=tgt)
            G.add_edge(attr_id, tgt_id, type='attribute_edge')
            G.add_edge(src_id, tgt_id, type='relation_edge', value=rel)

        elif rel_type == 'att|obj-att|obj' and len(content) == 5:
            attr1, src, rel, attr2, tgt = content
            attr1_id = f'attribute|auto|{attr1}'
            src_id = f'object|auto|{src}'
            attr2_id = f'attribute|auto|{attr2}'
            tgt_id = f'object|auto|{tgt}'
            G.add_node(attr1_id, type='attribute_node', value=attr1)
            G.add_node(src_id, type='object_node', value=src)
            G.add_node(attr2_id, type='attribute_node', value=attr2)
            G.add_node(tgt_id, type='object_node', value=tgt)
            G.add_edge(attr1_id, src_id, type='attribute_edge')
            G.add_edge(attr2_id, tgt_id, type='attribute_edge')
            G.add_edge(src_id, tgt_id, type='relation_edge', value=rel)

    return G

def get_knowledge(G, situ = None, llm_correct = False):
    cue_types = ['att|obj', 'obj-obj', 'att|obj-obj', 'obj-att|obj', 'att|obj-att|obj']
    cues = {
        cue_type:extract_knowledge(
        G, cue_type=cue_type,
        ) for cue_type in cue_types
    }
    return cues

def get_max_attribute(G, object_id):
    object_num = int(object_id.split('_')[1])
    max_attr_idx = 0
    for node in G.nodes():
        if isinstance(node, str) and node.startswith('attribute|'):
            parts = node.split('|')
            if len(parts) == 3:
                node_obj_idx = int(parts[1])
                attr_idx = int(parts[2])
                if node_obj_idx == object_num and attr_idx > max_attr_idx:
                    max_attr_idx = attr_idx

    return max_attr_idx
