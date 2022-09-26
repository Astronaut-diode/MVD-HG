# coding=UTF-8
import os
import re
import config
import json
import utils


# 将每一个工程文件夹中的内容转化成的抽象语法树节点转化为节点向量。注意这里面保存的节点的id都是从1开始的。
# project_node_list:代表所有的节点
# graph_dataset_dir_path:代表当前记录的工程文件夹的路径
def built_vector_dataset(project_node_list, file_name, word2vec_model):
    # 对应的raw文件夹路径，因为传入的是AST_json中的部分，所以需要转化为raw的部分。
    raw_project_dir_path = os.path.dirname(file_name).replace("AST_json", "raw")
    # 文件夹里面文件的全路径，但是不包含拓展名。这里映射到了raw文件夹中，是为了待会用来创建三个基本文件。
    raw_project_dir_half_name = file_name.replace("AST_json", "raw").replace(".json", "")
    # 这时候说明才存在模型，可以用来生成三个基本文件。
    # 如果是预测的时候，也需要生成对应的向量文件，用来计算结果。
    if config.create_corpus_mode == "generate_all" or config.run_mode == "predict":
        # 先根据节点id进行排序。
        project_node_list.sort(key=lambda obj: obj.node_id)
        # 在数组中节点一开始的节点id——正确对应的元素的id应该是多少
        id_mapping_id = {}
        # 遍历原始的节点序列，生成两个数组
        for index, node in enumerate(project_node_list):
            id_mapping_id[node.node_id] = index + 1
        # 首先，判断对应的文件夹是否存在
        utils.dir_exists(raw_project_dir_path)
        # 下面这三个函数都增加了节点的映射，这样子既能获取正确的节点间关系，还能获取正确的节点id，删除空白。
        # 传入所有的节点信息，生成对应的节点特征文件。
        create_node_feature_json(project_node_list, raw_project_dir_half_name, id_mapping_id, word2vec_model)
        # 传入所有的节点信息，生成抽象语法树的边文件。
        create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
        # 传入所有的节点信息，生成控制流边的边文件。
        create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
        # 传入所有的节点信息，生成数据流边的边文件。
        create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
        utils.success(f"{file_name}节点和边文件已经构建完毕。")


# 创建保存节点信息的json文件,注意，这里保存的结果点进去看只有一行，主要是为了减少保存的空间，如果想要好看，可以复制的json格式化的在线网站上看。
def create_node_feature_json(project_node_list, raw_project_dir_half_name, id_mapping_id, word2vec_model):
    # 先创建对应的节点特征的json文件,node.json
    node_feature_file_name = f'{raw_project_dir_half_name}_node.json'
    # 用来保存文件的句柄
    utils.create_file(node_feature_file_name)
    node_feature_handle = open(node_feature_file_name, 'w', encoding="UTF-8")
    # 保存到json文件中的节点列表
    node_feature_list = []
    # 遍历所有的节点，待会一一操作，保存到node_feature_list中去。
    for node in project_node_list:
        node_feature = word2vec_model[node.node_type]
        # 判断这个节点是否含有string字符串或者数字或者是方法名，如果有，需要一起添加进去，而且要注意大小驼峰的分割。
        tmp = have_attribute(node)
        # 如果有返回值，那就所说明确实是含有字符串或者数字或者方法名的
        if tmp:
            # 如果弹出的内容是str或者int类型，才会选择将他们添加到词库当中去。
            if isinstance(tmp[0], str) or isinstance(tmp[0], int):
                # 如果是方法名，那是需要进行大小驼峰的转化的
                for s in hump2sub(tmp[0]):
                    # 如果实在不存在，那就算了。
                    if s in word2vec_model:
                        # 将拆分以后的结果一个个的添加到向量中。
                        node_feature = node_feature + word2vec_model[s]
        # 第一规则：根据每一个节点的类型，获取他的向量化表示
        obj = {"node_id": id_mapping_id[node.node_id], "node_feature": node_feature.tolist()}
        # 添加到数组中，循环结束直接录入到节点特征文件当中。
        node_feature_list.append(obj)
    # 将节点信息保存到文件当中去。
    json.dump(node_feature_list, node_feature_handle, ensure_ascii=False)
    # 关闭句柄文件。
    node_feature_handle.close()
    utils.success(f"{node_feature_file_name}节点特征文件已经构建完毕")


# 判断这个节点是否包含了name，Literal或者value
def have_attribute(node):
    # 如果含有value的信息
    if "value" in node.attribute.keys():
        return node.attribute["value"]
    # 如果含有名字
    if "name" in node.attribute.keys():
        return node.attribute["name"]
    if "src_code" in node.attribute.keys():
        return node.attribute["src_code"]
    return None


# 拆分原始的大小驼峰信息
def hump2sub(hump_str):
    hump_str = hump_str.replace("\n", " ")
    p = re.compile(r'([a-z]|\d)([A-Z])')
    sub = re.sub(p, r'\1_\2', hump_str).lower()
    q = re.compile(r'([a-z][a-z])([0-9])')
    new_sub = re.sub(q, r'\1_\2', sub)
    seq = re.split('_', new_sub)
    return seq


# 创建抽象语法树的边文件。
def create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id):
    # 先创建对应的抽象语法树边信息的json文件,ast_edge.json
    ast_edge_file_name = f'{raw_project_dir_half_name}_ast_edge.json'
    # 用来保存文件的句柄
    utils.create_file(ast_edge_file_name)
    ast_edge_handle = open(ast_edge_file_name, 'w', encoding="UTF-8")
    # 保存到抽象语法树边信息中的节点列表
    ast_edge_list = []
    # 遍历所有的节点，待会一一操作，保存到ast_edge_list中去。
    for node in project_node_list:
        # 循环添加边
        for child in node.childes:
            obj = {"source_node_node_id": id_mapping_id[node.node_id], "target_node_node_id": id_mapping_id[child.node_id]}
            # 添加到数组中，循环结束直接录入到抽象语法树边信息文件当中。
            ast_edge_list.append(obj)
    # 将抽象语法树信息保存到文件当中去。
    json.dump(ast_edge_list, ast_edge_handle, ensure_ascii=False)
    # 关闭句柄文件。
    ast_edge_handle.close()
    utils.success(f"{ast_edge_file_name}抽象语法树边文件已经构建完毕")


# 创建控制流图的边文件。
def create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id):
    # 先创建对应的控制流图边信息的json文件,cfg_edge.json
    cfg_edge_file_name = f'{raw_project_dir_half_name}_cfg_edge.json'
    # 用来保存文件的句柄
    utils.create_file(cfg_edge_file_name)
    cfg_edge_handle = open(cfg_edge_file_name, 'w', encoding="UTF-8")
    # 保存到控制流图边信息中的节点列表
    cfg_edge_list = []
    # 遍历所有的节点，待会一一操作，保存到cfg_edge_list中去。
    for node in project_node_list:
        # 循环添加边
        for child in node.control_childes:
            obj = {"source_node_node_id": id_mapping_id[node.node_id], "target_node_node_id": id_mapping_id[child.node_id]}
            # 添加到数组中，循环结束直接录入到控制流边文件当中。
            cfg_edge_list.append(obj)
    # 将节点信息保存到文件当中去。
    json.dump(cfg_edge_list, cfg_edge_handle, ensure_ascii=False)
    # 关闭句柄文件。
    cfg_edge_handle.close()
    utils.success(f"{cfg_edge_file_name}控制流图边文件已经构建完毕")


# 创建数据流图的边文件。
def create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id):
    # 先创建对应的控制流图边信息的json文件,cfg_edge.json
    dfg_edge_file_name = f'{raw_project_dir_half_name}_dfg_edge.json'
    # 用来保存文件的句柄
    utils.create_file(dfg_edge_file_name)
    dfg_edge_handle = open(dfg_edge_file_name, 'w', encoding="UTF-8")
    # 保存到数据流图边信息中的节点列表
    dfg_edge_list = []
    # 遍历所有的节点，待会一一操作，保存到dfg_edge_list中去。
    for node in project_node_list:
        # 循环添加边
        for child in node.data_childes:
            obj = {"source_node_node_id": id_mapping_id[node.node_id], "target_node_node_id": id_mapping_id[child.node_id]}
            # 添加到数组中，循环结束直接录入到数据流边文件当中。
            dfg_edge_list.append(obj)
    # 将节点信息保存到文件当中去。
    json.dump(dfg_edge_list, dfg_edge_handle, ensure_ascii=False)
    # 关闭句柄文件。
    dfg_edge_handle.close()
    utils.success(f"{dfg_edge_file_name}数据流图边文件已经构建完毕")
