from gensim.models import Word2Vec
import os
import config
import json

data_dir_path = f'{os.getcwd()}/data/'
dataset_dir_path = f'{data_dir_path}/raw/'


# 将每一个工程文件夹中的内容转化成的抽象语法树节点转化为节点向量。注意这里面保存的节点的id都是从1开始的。
# project_node_list:代表所有的节点
# graph_dataset_dir_path:代表当前记录的工程文件夹的路径
def built_vector_dataset(project_node_list, graph_dataset_dir_path):
    # 先根据节点id进行排序。
    project_node_list.sort(key=lambda node: node.node_id)
    # 首先，判断对应的文件夹是否存在
    if not os.path.exists(graph_dataset_dir_path):
        os.makedirs(graph_dataset_dir_path)
    # 传入所有的节点信息，生成对应的节点特征文件。
    create_node_feature_json(project_node_list, graph_dataset_dir_path)
    # 传入所有的节点信息，生成抽象语法树的边文件。
    create_ast_edge_json(project_node_list, graph_dataset_dir_path)
    # 传入所有的节点信息，生成控制流边的边文件。
    create_cfg_edge_json(project_node_list, graph_dataset_dir_path)


# 创建保存节点信息的json文件,注意，这里保存的结果点进去看只有一行，主要是为了减少保存的空间，如果想要好看，可以复制的json格式化的在线网站上看。
def create_node_feature_json(project_node_list, graph_dataset_dir_path):
    # 先创建对应的节点特征的json文件,node.json
    node_feature_file_name = graph_dataset_dir_path + "node.json"
    # 用来保存文件的句柄
    node_feature_handle = open(node_feature_file_name, 'w', encoding="UTF-8")
    # 保存到json文件中的节点列表
    node_feature_list = []
    # 加载词向量的模型
    word2vec_model = Word2Vec.load(config.corpus_file_path).wv
    # 遍历所有的节点，待会一一操作，保存到node_feature_list中去。
    for node in project_node_list:
        # 第一规则：根据每一个节点的类型，获取他的向量化表示
        obj = {"node_id": node.node_id, "node_feature": word2vec_model[node.node_type].tolist()}
        # 添加到数组中，循环结束直接录入到节点特征文件当中。
        node_feature_list.append(obj)
    # 将节点信息保存到文件当中去。
    json.dump(node_feature_list, node_feature_handle, ensure_ascii=False)
    # 关闭句柄文件。
    node_feature_handle.close()
    print(f"{node_feature_file_name}节点特征文件已经构建完毕")


# 创建抽象语法树的边文件。
def create_ast_edge_json(project_node_list, graph_dataset_dir_path):
    # 先创建对应的抽象语法树边信息的json文件,ast_edge.json
    ast_edge_file_name = graph_dataset_dir_path + "ast_edge.json"
    # 用来保存文件的句柄
    ast_edge_handle = open(ast_edge_file_name, 'w', encoding="UTF-8")
    # 保存到抽象语法树边信息中的节点列表
    ast_edge_list = []
    # 遍历所有的节点，待会一一操作，保存到ast_edge_list中去。
    for node in project_node_list:
        # 循环添加边
        for child in node.childes:
            obj = {"source_node_node_id": node.node_id, "target_node_node_id": child.node_id}
            # 添加到数组中，循环结束直接录入到抽象语法树边信息文件当中。
            ast_edge_list.append(obj)
    # 将抽象语法树信息保存到文件当中去。
    json.dump(ast_edge_list, ast_edge_handle, ensure_ascii=False)
    # 关闭句柄文件。
    ast_edge_handle.close()
    print(f"{ast_edge_file_name}抽象语法树边文件已经构建完毕")


# 创建控制流图的边文件。
def create_cfg_edge_json(project_node_list, graph_dataset_dir_path):
    # 先创建对应的控制流图边信息的json文件,cfg_edge.json
    cfg_edge_file_name = graph_dataset_dir_path + "cfg_edge.json"
    # 用来保存文件的句柄
    cfg_edge_handle = open(cfg_edge_file_name, 'w', encoding="UTF-8")
    # 保存到控制流图边信息中的节点列表
    cfg_edge_list = []
    # 遍历所有的节点，待会一一操作，保存到cfg_edge_list中去。
    for node in project_node_list:
        # 循环添加边
        for child in node.control_childes:
            obj = {"source_node_node_id": node.node_id, "target_node_node_id": child.node_id}
            # 添加到数组中，循环结束直接录入到控制流边文件当中。
            cfg_edge_list.append(obj)
    # 将节点信息保存到文件当中去。
    json.dump(cfg_edge_list, cfg_edge_handle, ensure_ascii=False)
    # 关闭句柄文件。
    cfg_edge_handle.close()
    print(f"{cfg_edge_file_name}控制流图边文件已经构建完毕")
