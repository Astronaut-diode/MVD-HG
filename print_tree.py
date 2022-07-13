# coding=UTF-8
import networkx as nx
import matplotlib.pyplot as plt
import datetime
import config

# 设置生成的图片的尺寸，单位是inches
plt.rcParams['figure.figsize'] = (config.img_width, config.img_height)


# 以图的形式绘制出树，方便检查是否正确
def print_tree(project_node_list):
    g = nx.MultiDiGraph()  # 无多重边有向图
    # 记录每一层已经被用了多少个位置，这个数组只要比树的最大深度深就行
    now_len_in_deep = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    # 记录每个节点出现的位置
    pos = {}
    # 循环遍历每一个节点
    for node in project_node_list:
        # 判断是否需要忽略某些节点
        if config.ignore_AST_some_list:
            # 如果需要忽略，判断当前节点是否属于被忽略的节点的类型。
            if node.node_type in config.ignore_list:
                continue
        # 如果不是被忽略的类型，可以直接添加到图上。
        g.add_node(node)
        # 同时获取这个节点的深度。
        deep = _get_deep(node)
        # 将这个节点的位置设定为[深度, 对应的位置 + 1]
        pos[node] = [deep, now_len_in_deep[deep] + 1]
        # 更新这一层已经用了多少个格子
        now_len_in_deep[deep] = now_len_in_deep[deep] + 1
    # 根据节点的类型设定好颜色。
    color_map = []
    # 根据节点的类型去获取节点应该显示的颜色，如果不在预设的内容中，设定为灰色。
    for node in g:
        if node.node_type in config.color_dict.keys():
            color_map.append(config.color_dict[node.node_type])
        else:
            color_map.append('grey')
    # 绘制节点和节点的标签。
    nx.draw_networkx_nodes(g, pos=pos, node_color=color_map)
    nx.draw_networkx_labels(g, pos=pos, font_size=10)
    # 如果需要绘制抽象语法树
    if config.show_AST_plt:
        # 重新遍历，绘制抽象语法树的边，因为如果在上一个循环内就添加边，那时候子节点还没有被添加进去，所以是无法添加边的，会出现异常情况。
        for node in project_node_list:
            # 循环当前节点的所有子节点
            for child in node.childes:
                # 如果一条边的两个节点都在图上，那才能绘制，否则不可以绘制。
                if node in g.nodes and child in g.nodes:
                    # 绘制边。
                    nx.draw_networkx_edges(g, pos, edgelist=[(node, child)], width=0.5, edge_color="black", style="solid", arrowsize=10)
    # 下面是关于CFG的图绘制，如果需要绘制CFG边。
    if config.show_CFG_plt:
        # 循环图上的所有节点。
        for node in project_node_list:
            # 循环其中的每一个子节点
            for control_child in node.control_childes:
                # 如果一条边的两个节点都存在，才允许绘制。
                if node in g.nodes and control_child in g.nodes:
                    nx.draw_networkx_edges(g, pos, edgelist=[(node, control_child)], width=2, edge_color="brown", style="-.", arrowsize=20)
    # 获取当前系统时间
    time = datetime.datetime.now()
    time.strftime("%Y-%m-%d %H:%M")
    # 文件的名字：/home/xjj/AST-GNN/img/时间.png
    png_name = "./img/" + str(time) + str(len(project_node_list)) + ".png"
    # 保存为图片
    plt.savefig(png_name)
    # 回显一下。
    plt.show()


# 不断递归这个节点的父节点，就能找到这个节点的深度
def _get_deep(node):
    ans = 0
    while node.parent is not None:
        ans = ans + 1
        node = node.parent
    return ans
