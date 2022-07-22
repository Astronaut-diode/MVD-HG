# coding=UTF-8
import config
import os
import utils
import pygraphviz as pgv


# 生成对应文件的dot文件
def generate_svg(project_node_list, file_name):
    if not config.show_plt:
        return
    G = pgv.AGraph(directed=True, strict=False, nodesep=1, ranksep=1, rankdir="TB", splines="spline", concentrate=True)
    # 循环遍历每一个节点
    for node in project_node_list:
        # 判断是否需要忽略某些节点
        if config.ignore_AST_some_list:
            # 如果需要忽略，判断当前节点是否属于被忽略的节点的类型。
            if node.node_type in config.ignore_list:
                continue
        # 判断节点类型是否已经在预设列表中，如果在，直接使用预设的颜色。
        if node.node_type in config.color_dict.keys():
            G.add_node(node.node_id, label=node.node_type, color=config.color_dict[node.node_type], style="filled")
        else:
            G.add_node(node.node_id, label=node.node_type, color="grey", style="filled")
    # 如果需要绘制抽象语法树
    if config.show_AST_plt:
        # 重新遍历，绘制抽象语法树的边，因为如果在上一个循环内就添加边，那时候子节点还没有被添加进去，所以是无法添加边的，会出现异常情况。
        for node in project_node_list:
            source_node = str(node.node_id)
            # 循环当前节点的所有子节点
            for child in node.childes:
                target_node = str(child.node_id)
                # 如果一条边的两个节点都在图上，那才能绘制，否则不可以绘制。
                if source_node in G.nodes() and target_node in G.nodes():
                    G.add_edge(source_node, target_node, color="black", label="AST", arrowsize=1.5, penwidth=2)
    # 下面是关于CFG的图绘制，如果需要绘制CFG边。
    if config.show_CFG_plt:
        # 循环图上的所有节点。
        for node in project_node_list:
            source_node = str(node.node_id)
            # 循环其中的每一个子节点
            for control_child in node.control_childes:
                target_node = str(control_child.node_id)
                # 如果一条边的两个节点都存在，才允许绘制。
                if source_node in G.nodes() and target_node in G.nodes():
                    G.add_edge(source_node, target_node, color="brown", label="CFG", arrowsize=1.5, penwidth=2)
    # 下面是关于DFG的图绘制，如果需要绘制DFG边。
    if config.show_DFG_plt:
        # 循环图上的所有节点。
        for node in project_node_list:
            source_node = str(node.node_id)
            # 循环其中的每一个子节点
            for data_child in node.data_childes:
                target_node = str(data_child.node_id)
                # 如果一条边的两个节点都存在，才允许绘制。
                if source_node in G.nodes() and target_node in G.nodes():
                    G.add_edge(source_node, target_node, color="red", label="DFG", arrowsize=1.5, penwidth=2)
    G.layout()
    # 当前文件的目录文件夹
    project_img_dir = os.path.dirname(f"{file_name.replace('AST_json', 'img').replace('.json', '.svg')}")
    # 先创建对应的文件夹
    utils.dir_exists(project_img_dir)
    # 在这里面生成图片文件
    G.draw(f"{file_name.replace('AST_json', 'img').replace('.json', '.svg')}", prog="dot")
