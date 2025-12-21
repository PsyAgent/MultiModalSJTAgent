from __future__ import annotations

import matplotlib.pyplot as plt
import networkx as nx
from matplotlib import colormaps as cm

from ..utils.graph_utils import map_knowledge
plt.rcParams['font.family'] = 'Comic Sans MS'
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.family'] = 'Songti SC'

def _expand_limits_to_include_texts(ax, pad_frac=0.05):
    """
    将轴内所有文本(Text)的像素外接框扩展并映射回数据坐标，
    扩张当前 ax 的 xlim/ylim，确保文本不会被裁切。
    pad_frac: 额外边距占当前范围比例
    """
    fig = ax.figure
    # 必须先触发一次 draw，确保 text 的布局/包围盒已计算
    fig.canvas.draw()

    if not ax.texts:
        return

    # 当前数据范围
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    inv = ax.transData.inverted()

    # 收集所有文本的像素包围盒 -> 数据坐标
    xmins, xmaxs, ymins, ymaxs = [x0], [x1], [y0], [y1]
    for t in ax.texts:
        # 忽略不可见对象
        if not t.get_visible():
            continue
        bbox = t.get_window_extent(renderer=fig.canvas.get_renderer())
        # 四个角点(像素坐标) -> 数据坐标
        corners_disp = [
            (bbox.x0, bbox.y0), (bbox.x0, bbox.y1),
            (bbox.x1, bbox.y0), (bbox.x1, bbox.y1)
        ]
        corners_data = [inv.transform(c) for c in corners_disp]
        xs, ys = zip(*corners_data)
        xmins.append(min(xs))
        xmaxs.append(max(xs))
        ymins.append(min(ys))
        ymaxs.append(max(ys))

    nx0, nx1 = min(xmins), max(xmaxs)
    ny0, ny1 = min(ymins), max(ymaxs)

    # 计算边距并扩张
    xpad = (nx1 - nx0) * pad_frac if nx1 > nx0 else 1e-3
    ypad = (ny1 - ny0) * pad_frac if ny1 > ny0 else 1e-3
    ax.set_xlim(nx0 - xpad, nx1 + xpad)
    ax.set_ylim(ny0 - ypad, ny1 + ypad)


def draw_G(
    G,
    ax=None,
    figsize=(6, 6),
    title='',
    node_fontsize=10,
    edge_fontsize=10,
    node_size=800,
    dpi=300,
    show_node_value=True,
    show_edge_value=True,
    object_node_color='skyblue',
    attribute_node_color='pink',
    relation_edge_color='black',
    attribute_edge_color='lightgray',
    object_node_edge_color='white',
    attribute_node_edge_color='white',
    colors=None,
    layout='spring',
    attribute_node_shape='o',
    object_node_shape='o',
    font_family='Songti SC',
):
    """
    绘制场景图 G，并保证文本不会被裁切（见 _expand_limits_to_include_texts）。
    """
    # 选择布局
    if layout == 'spring':
        pos = nx.spring_layout(G, seed=42, k=3)
    elif layout == 'circular':
        pos = nx.circular_layout(G)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(G)
    elif layout == 'shell':
        pos = nx.shell_layout(G)
    else:
        pos = nx.spring_layout(G, seed=42, k=0.8)

    returnfig = False
    if ax is None:
        returnfig = True
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi, constrained_layout=False)
    else:
        fig = ax.figure

    # 分边类型
    relation_edges = [(u, v) for u, v, data in G.edges(data=True) if data.get('type') == 'relation_edge']
    attribute_edges = [(u, v) for u, v, data in G.edges(data=True) if data.get('type') == 'attribute_edge']

    # 关系边颜色
    relation_edge_colors = []
    for u, v in relation_edges:
        data = G.get_edge_data(u, v)
        edge_key = data.get('id', (u, v))
        if colors and 'edge' in colors:
            edge_color = colors['edge'].get(edge_key, relation_edge_color)
        else:
            edge_color = relation_edge_color
        relation_edge_colors.append(edge_color)

    # 属性边颜色
    attribute_edge_colors = []
    for u, v in attribute_edges:
        data = G.get_edge_data(u, v)
        edge_key = data.get('id', (u, v))
        if colors and 'edge' in colors:
            edge_color = colors['edge'].get(edge_key, attribute_edge_color)
        else:
            edge_color = attribute_edge_color
        attribute_edge_colors.append(edge_color)

    # 绘制边
    nx.draw_networkx_edges(
        G, pos, edgelist=relation_edges, ax=ax,
        arrowstyle='-|>', arrowsize=20, width=2, edge_color=relation_edge_colors,
        min_source_margin=15, min_target_margin=15, connectionstyle='arc3, rad=.1',
    )
    nx.draw_networkx_edges(
        G, pos, edgelist=attribute_edges, ax=ax,
        arrowstyle='-|>', arrowsize=20, width=2, edge_color=attribute_edge_colors,
        min_source_margin=15, min_target_margin=15,
    )

    # 节点
    object_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'object_node']
    attribute_nodes = [n for n, d in G.nodes(data=True) if d.get('type') == 'attribute_node']

    if colors and 'node' in colors:
        object_fill_colors, object_border_colors = [], []
        for node in object_nodes:
            if node in colors['node']:
                fill, border = colors['node'][node]
            else:
                fill, border = object_node_color, object_node_edge_color
            object_fill_colors.append(fill); object_border_colors.append(border)
        nx.draw_networkx_nodes(
            G, pos, nodelist=object_nodes, ax=ax,
            node_size=node_size, node_color=object_fill_colors,
            node_shape=object_node_shape, edgecolors=object_border_colors, linewidths=1.5,
        )
    else:
        nx.draw_networkx_nodes(
            G, pos, nodelist=object_nodes, ax=ax,
            node_size=node_size, node_color=object_node_color,
            node_shape=object_node_shape, edgecolors=object_node_edge_color, linewidths=1.5,
        )

    if colors and 'node' in colors:
        attribute_fill_colors, attribute_border_colors = [], []
        for node in attribute_nodes:
            if node in colors['node']:
                fill, border = colors['node'][node]
            else:
                fill, border = attribute_node_color, attribute_node_edge_color
            attribute_fill_colors.append(fill); attribute_border_colors.append(border)
        nx.draw_networkx_nodes(
            G, pos, nodelist=attribute_nodes, ax=ax,
            node_size=node_size, node_color=attribute_fill_colors,
            node_shape=attribute_node_shape, edgecolors=attribute_border_colors, linewidths=1.5,
        )
    else:
        nx.draw_networkx_nodes(
            G, pos, nodelist=attribute_nodes, ax=ax,
            node_size=node_size, node_color=attribute_node_color,
            node_shape=attribute_node_shape, edgecolors=attribute_node_edge_color, linewidths=1.5,
        )

    # 节点标签
    if show_node_value:
        labels = {n: d.get('value', n) for n, d in G.nodes(data=True)}
        node_texts = nx.draw_networkx_labels(
            G, pos, labels=labels, ax=ax, font_size=node_fontsize, font_color='black',
            font_family=font_family
        )
        if colors and 'label' in colors:
            for n, text in node_texts.items():
                text.set_color(colors['label'].get(n, 'black'))

    # 边标签（仅 relation_edge）
    if show_edge_value:
        edge_labels = {(u, v): d.get('value', '') for u, v, d in G.edges(data=True) if d.get('type') == 'relation_edge'}
        edge_texts = nx.draw_networkx_edge_labels(
            G, pos, edge_labels=edge_labels, ax=ax, font_size=edge_fontsize,
            label_pos=0.5, bbox=dict(facecolor='none', edgecolor='none', pad=0.5),
            font_family=font_family
        )
        if colors and 'label' in colors:
            for e, text in edge_texts.items():
                text.set_color(colors['label'].get(e, 'black'))

    # 先给出基础范围（考虑节点坐标），再统一自适应
    x_vals, y_vals = zip(*pos.values())
    x_min, x_max = min(x_vals), max(x_vals)
    y_min, y_max = min(y_vals), max(y_vals)
    x_padding = max(1e-6, (x_max - x_min) * 0.2)
    y_padding = max(1e-6, (y_max - y_min) * 0.2)
    ax.set_xlim(x_min - x_padding, x_max + x_padding)
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    ax.set_aspect('equal', adjustable='datalim')
    ax.relim()
    ax.autoscale_view()
    ax.margins(0.10)

    # 重点：把文本的实际像素范围也纳入轴域
    _expand_limits_to_include_texts(ax, pad_frac=0.08)

    ax.set_title(title, fontsize=16)

    if returnfig:
        for side in ['top', 'bottom', 'left', 'right']:
            ax.spines[side].set_visible(False)
        ax.axis('off')
        return fig


def draw_Gs(Gs):
    """
    多子图绘制，逐轴调用 draw_G 后，再次用 _expand_limits_to_include_texts
    做一次“兜底”扩张，避免相邻子图挤压造成的文本裁切。
    """
    vng_map = {
        'E': 'Establisher',
        'I': 'Initial',
        'Pr': 'Prolongation',
        'P': 'Peak',
    }

    n = len(Gs)
    if n == 1:
        fig, ax = plt.subplots(1, 1, figsize=(4, 4), dpi=300, constrained_layout=False)
        vng = list(Gs.keys())[0]
        draw_G(Gs[vng], ax=ax, title=vng_map.get(vng, str(vng)), node_fontsize=8, edge_fontsize=8)
        for side in ['top', 'bottom', 'left']:
            ax.spines[side].set_visible(False)
        # ax.axis('off')
        # 单图也做一次兜底
        _expand_limits_to_include_texts(ax, pad_frac=0.08)
        return fig
    else:
        fig, axs = plt.subplots(1, n, figsize=(4*n, 4), dpi=300, constrained_layout=False)

        for i, (vng, G) in enumerate(Gs.items()):
            ax = axs[i]
            draw_G(G, ax=ax, title=vng_map.get(vng, str(vng)), node_fontsize=8, edge_fontsize=8)
            for side in ['top', 'bottom', 'left', 'right']:
                ax.spines[side].set_visible(False)
            ax.axis('off')
            # 对每个子图单独做一次“文本外延并入数据范围”的扩张
            _expand_limits_to_include_texts(ax, pad_frac=0.08)

        # 子图之间留一点空隙，避免视觉拥挤；不使用 tight_layout，以免再次压缩轴域
        fig.subplots_adjust(left=0.04, right=0.98, top=0.92, bottom=0.06, wspace=0.08, hspace=0.02)
        return fig

def draw_G_cue_highlight(G, cues, cmap='hsv', title=None, **kwargs):
    """
    绘制场景图G，并高亮显示指定的cues

    参数:
    G: nx.DiGraph 对象，场景图
    cues: 需要高亮显示的cues列表
    cmap: 颜色映射名称，默认为'hsv'
    title: 图标题，默认为'SituCues'
    **kwargs: 传递给draw_G的其他参数

    返回:
    matplotlib.figure.Figure 对象
    """

    def get_colors_by_cues(G, cues, cmap='gist_ncar'):
        def custom_cmap(value):
            colormap = cm.get_cmap(cmap)
            return colormap(value)

        colors_cue = [custom_cmap(i / len(cues)) for i in range(len(cues))]
        gh_id = [map_knowledge(G, cue['content'], cue['type']) for cue in cues]
        colors = {'edge': {}, 'label': {}}
        for i, cue in enumerate(gh_id):
            color = colors_cue[i]
            # 检查cue是否为None
            if cue is None:
                continue
            for j in cue:
                if isinstance(j, tuple):  # 处理关系边
                    colors['edge'][j] = color
                    colors['label'][j] = color
                if 'attribute' in j:  # 处理属性边
                    colors['edge'][(j, f'object_{j.split("|")[-2]}')] = color
                    colors['label'][(j, f'object_{j.split("|")[-2]}')] = color
        return colors

    # 获取高亮颜色
    colors = get_colors_by_cues(G, cues, cmap=cmap)

    # 设置默认参数
    default_kwargs = {
        'attribute_edge_color': 'black',
        'attribute_node_shape': '^',
        'object_node_color': 'lightgray',
        'attribute_node_color': 'lightgray',
        'title': title,
    }

    # 更新参数
    for key, value in default_kwargs.items():
        if key not in kwargs:
            kwargs[key] = value

    # 调用draw_G函数绘制图
    return draw_G(G, colors=colors, **kwargs)
