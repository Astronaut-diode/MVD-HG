import json

from gensim.models.word2vec import Word2Vec
from remove_comments import remove_comments
from compile_files import compile_files
from read_compile import read_compile
from append_method_message_by_dict import append_method_message_by_dict
from append_control_flow_information import append_control_flow_information
from append_data_flow_information import append_data_flow_information
from built_corpus import built_corpus_bfs, built_corpus_dfs
from built_vector_dataset import built_vector_dataset
from print_tree import generate_svg
from torch_geometric.data import Data
import utils
import os
from tqdm import tqdm
from line_classification.line_classification_dataset import line_classification_dataset
from contract_classification.contract_classification_dataset import contract_classification_dataset
from torch_geometric.nn import MessagePassing, global_mean_pool, Linear, RGCNConv, RGATConv, GATConv
from typing import Optional
from torch import Tensor
from torch.nn import ReLU, Sigmoid, Dropout
from torch_sparse import SparseTensor
import config
import torch


def load_model_to_predict_line():
    # 挑选出最优秀的模型
    max_score = 0
    max_mode_file = os.listdir(config.model_data_dir)[0]
    for model_file in os.listdir(config.model_data_dir):
        score = float(model_file.replace(".pth", "").split("_")[3])
        if score > max_score:
            max_score = score
            max_mode_file = model_file
    import datetime
    b1 = datetime.datetime.now()
    model = line_classification_model_for_predict()
    # 加载原始保存的参数
    model_params_dict = torch.load(os.path.join(config.model_data_dir, max_mode_file))
    best_threshold = model_params_dict["best_threshold"]
    # 将加载的参数添加到模型当中去
    model.load_state_dict(model_params_dict["model_params"])
    # 加载词向量的模型,在这里加载是为了服务所有需要被检验的文件。
    word2vec_model = Word2Vec.load(config.corpus_file_path).wv
    dangerous_count = 0
    safe_count = 0
    exception_count = 0
    detect_res = f"{config.wait_predict_fold}/res_line.json"
    res_list = []
    if os.path.exists(detect_res):  # 如果文件存在，读取一下
        with open(detect_res, 'r') as res:
            res_list = json.load(res)
    e1 = datetime.datetime.now()
    utils.tip(f"加载模型一共耗时:{e1 - b1}")
    # 遍历wait_pre下的
    for project_name in tqdm(os.listdir(config.wait_predict_sol_source_fold)):
        if not project_name == config.target_dir:
            continue
        # wait_predict/sol_source/下面所有的工程文件夹
        sol_source_project_dir_path = f'{config.wait_predict_sol_source_fold}/{project_name}'
        ast_json_project_dir_path = f'{config.wait_predict_ast_json_fold}/{project_name}'
        import datetime
        b2 = datetime.datetime.now()
        # 删除源文件中的注释
        remove_comments(data_sol_source_project_dir_path=sol_source_project_dir_path)
        # 编译sol_source下工程文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
        compile_files(data_sol_source_project_dir_path=sol_source_project_dir_path,
                      data_ast_json_project_dir_path=ast_json_project_dir_path)
        # 遍历这个json文件的文件夹，取出其中所有的子文件夹
        for now_dir, child_dirs, child_files in os.walk(ast_json_project_dir_path):
            if not now_dir.endswith(config.target_dir):
                continue
            # 遍历工程项目中的每一个文件
            for ast_json_file_name in child_files:
                if not ast_json_file_name == config.target_file.replace(".sol", ".json"):
                    continue
                try:
                    # 读取刚刚记录下来的抽象语法树的json文件
                    project_node_list, project_node_dict = read_compile(now_dir=now_dir,
                                                                        ast_json_file_name=ast_json_file_name)
                    # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
                    append_method_message_by_dict(project_node_dict=project_node_dict,
                                                  file_name=f"{now_dir}/{ast_json_file_name}")
                    # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
                    append_control_flow_information(project_node_list=project_node_list,
                                                    project_node_dict=project_node_dict,
                                                    file_name=f"{now_dir}/{ast_json_file_name}")
                    # 根据内存中的数据，设定图的数据流。
                    append_data_flow_information(project_node_list=project_node_list,
                                                 project_node_dict=project_node_dict,
                                                 file_name=f"{now_dir}/{ast_json_file_name}")
                    try:
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list,
                                             file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)
                        # 先根据节点id进行排序。
                        project_node_list.sort(key=lambda obj: obj.node_id)
                        # 在数组中节点一开始的节点id——正确对应的元素的id应该是多少
                        id_mapping_id = {}
                        # 遍历原始的节点序列，生成两个数组
                        for index, node in enumerate(project_node_list):
                            id_mapping_id[node.node_id] = index + 1

                        from built_vector_dataset import create_node_feature_json, create_ast_edge_json, \
                            create_cfg_edge_json, create_dfg_edge_json
                        file_name = now_dir + "/" + ast_json_file_name
                        # 对应的raw文件夹路径，因为传入的是AST_json中的部分，所以需要转化为raw的部分。
                        raw_project_dir_path = os.path.dirname(file_name).replace("AST_json", "raw")
                        # 文件夹里面文件的全路径，但是不包含拓展名。这里映射到了raw文件夹中，是为了待会用来创建三个基本文件。
                        raw_project_dir_half_name = file_name.replace("AST_json", "raw").replace(".json", "")
                        # 首先，判断对应的文件夹是否存在
                        utils.dir_exists(raw_project_dir_path)
                        # 下面这三个函数都增加了节点的映射，这样子既能获取正确的节点间关系，还能获取正确的节点id，删除空白。
                        # 传入所有的节点信息，生成对应的节点特征文件。
                        create_node_feature_json(project_node_list, raw_project_dir_half_name, id_mapping_id,
                                                 word2vec_model)
                        # 传入所有的节点信息，生成抽象语法树的边文件。
                        create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成控制流边的边文件。
                        create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成数据流边的边文件。
                        create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        utils.success(f"{file_name}节点和边文件已经构建完毕。")
                        e2 = datetime.datetime.now()
                        utils.tip(f"构建基础文件一共耗时:{e2 - b2}")
                    except Exception as e:
                        utils.error(f"{e}需要先更新词表")
                        # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
                        built_corpus_bfs(project_node_list=project_node_list,
                                         file_name=f"{now_dir}/{ast_json_file_name}")
                        built_corpus_dfs(project_node_list=project_node_list,
                                         file_name=f"{now_dir}/{ast_json_file_name}")
                        # 加载词向量的模型,在这里加载是因为原始的文本库模型文件可能被修改了，但是读入的是原始的。
                        word2vec_model = Word2Vec.load(config.corpus_file_path).wv
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list,
                                             file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)

                        # 先根据节点id进行排序。
                        project_node_list.sort(key=lambda obj: obj.node_id)
                        # 在数组中节点一开始的节点id——正确对应的元素的id应该是多少
                        id_mapping_id = {}
                        # 遍历原始的节点序列，生成两个数组
                        for index, node in enumerate(project_node_list):
                            id_mapping_id[node.node_id] = index + 1

                        from built_vector_dataset import create_node_feature_json, create_ast_edge_json, \
                            create_cfg_edge_json, create_dfg_edge_json
                        file_name = now_dir + "/" + ast_json_file_name
                        # 对应的raw文件夹路径，因为传入的是AST_json中的部分，所以需要转化为raw的部分。
                        raw_project_dir_path = os.path.dirname(file_name).replace("AST_json", "raw")
                        # 文件夹里面文件的全路径，但是不包含拓展名。这里映射到了raw文件夹中，是为了待会用来创建三个基本文件。
                        raw_project_dir_half_name = file_name.replace("AST_json", "raw").replace(".json", "")
                        # 首先，判断对应的文件夹是否存在
                        utils.dir_exists(raw_project_dir_path)
                        # 下面这三个函数都增加了节点的映射，这样子既能获取正确的节点间关系，还能获取正确的节点id，删除空白。
                        # 传入所有的节点信息，生成对应的节点特征文件。
                        create_node_feature_json(project_node_list, raw_project_dir_half_name, id_mapping_id,
                                                 word2vec_model)
                        # 传入所有的节点信息，生成抽象语法树的边文件。
                        create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成控制流边的边文件。
                        create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成数据流边的边文件。
                        create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        utils.success(f"{file_name}节点和边文件已经构建完毕。")
                        e2 = datetime.datetime.now()
                        utils.tip(f"构建基础文件一共耗时:{e2 - b2}")
                    # 打印树的样子。
                    generate_svg(project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")

                    # 获取对应raw工程文件夹下的原始文件名_node.json文件中的内容。
                    node_feature = line_classification_dataset.get_x(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "node_feature")
                    # 智能合约文件中所有包含漏洞的代码行
                    contract_buggy_line = line_classification_dataset.get_contract_buggy_line(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    # 文件中当前所在contract的分类标签
                    contract_classification_label = line_classification_dataset.get_x(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "contract_label")
                    # 文件中当前所在行的分类标签
                    line_classification_label = line_classification_dataset.get_x(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "line_label")
                    # 当前行所处在的四种位置。
                    owner_file = line_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_file")
                    owner_contract = line_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_contract")
                    owner_function = line_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_function")
                    owner_line = line_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_line")
                    # 获取抽象语法树边的信息
                    ast_edge_index = line_classification_dataset.get_ast_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    # 创建边的属性
                    ast_edge_attr = torch.zeros(ast_edge_index.shape[1])
                    cfg_edge_index = line_classification_dataset.get_cfg_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    cfg_edge_attr = torch.zeros(cfg_edge_index.shape[1]) + 1
                    dfg_edge_index = line_classification_dataset.get_dfg_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    dfg_edge_attr = torch.zeros(dfg_edge_index.shape[1]) + 2
                    # 将上面三份内容一起使用，用来构造一份数据集。
                    edge_index = torch.cat((ast_edge_index, cfg_edge_index, dfg_edge_index), dim=1)
                    edge_attr = torch.cat((ast_edge_attr, cfg_edge_attr, dfg_edge_attr))
                    # 通过节点属性，边连接情况，边的属性，还有标签一起构建数据集。
                    predict_data = Data(x=node_feature,  # 节点特征
                                        edge_index=edge_index,  # 是一个[2, num(E)]的矩阵，代表边的连接情况。
                                        edge_attr=edge_attr,  # 象征每一条边分别是0，1，2用来代表原始边，控制流边，数据流边。
                                        conrtract_classification_label=contract_classification_label,
                                        # 每一个节点都有一个对应的合约标签
                                        line_classification_label=line_classification_label,  # 行标签
                                        owner_file=owner_file,  # 当前所属文件
                                        owner_contract=owner_contract,  # 当前节点所属合约
                                        owner_function=owner_function,  # 当前节点所属函数
                                        owner_line=owner_line,  # 当前节点所属行
                                        contract_buggy_line=contract_buggy_line)  # 当前节点对应的文件中所有的行，如果该行没有漏洞，那么值就是0，否则是1

                    predict = model(predict_data)
                    count = 0
                    res = []
                    for idx, p in enumerate(predict):
                        if p.item() >= best_threshold:
                            res.append(idx + 1)
                            utils.error(f"{ast_json_file_name}中第{idx + 1}行存在{config.attack_type_name}类型的漏洞")
                            count = count + 1
                    if count == 0:
                        utils.tip(f"{ast_json_file_name}中不存在{config.attack_type_name}类型的漏洞")

                    res_list.append(
                        {
                            "name": f"{file_name.replace('AST_json', 'sol_source').replace('.json', '.sol')}",
                            "label": res,
                            "attack_type": config.attack_type_name
                        }
                    )

                except Exception as e:
                    utils.success(f"{ast_json_file_name}执行过程中出现异常了{e}")
                    exception_count += 1
    # 准备将这个对象保存为json文件
    utils.save_json(res_list, f"{config.wait_predict_fold}/res_line.json")


class line_classification_model_for_predict(MessagePassing):
    def __init__(self):
        super(line_classification_model_for_predict, self).__init__()
        self.RGCNconv1 = RGCNConv(in_channels=300, out_channels=256, num_relations=3)
        self.RGCNconv2 = RGCNConv(in_channels=256, out_channels=128, num_relations=3)
        self.RGCNconv3 = RGCNConv(in_channels=128, out_channels=64, num_relations=3)
        self.RGCNconv4 = RGCNConv(in_channels=64, out_channels=32, num_relations=3)
        self.final_Linear = Linear(in_channels=32, out_channels=1)
        self.dropout = Dropout(p=config.dropout_pro)
        self.relu = ReLU()
        self.sigmoid = Sigmoid()

    def forward(self, data):
        x = self.RGCNconv1(data.x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv2(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv3(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv4(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)

        x = x.to(config.device)
        # 在这里根据合约的包含范围，对batch进行操作，然后找到需要返回的结果，同时需要用线性层继续学习一下。
        res = torch.tensor([]).to(config.device)
        # 依次循环遍历每一种contract
        for line in range(len(data.contract_buggy_line)):
            global_tmp = torch.zeros(x[0].shape).to(config.device)
            count = 0
            # 针对当前遍历的行号+1找出所有对应的节点
            for index, ite in enumerate(data.owner_line):
                # 如果名字匹配，那么index就说明找到目标节点了。
                # 兼容下上下两行的内容
                # 为了提高uncheck的精度，直接改成目标行。
                if ite in [line]:
                    global_tmp += x[index] * config.coefficient[1]
                    count += config.coefficient[1]
                if ite in [line - 1]:
                    global_tmp += x[index] * config.coefficient[0]
                    count += config.coefficient[0]
                if ite in [line + 1]:
                    global_tmp += x[index] * config.coefficient[2]
                    count += config.coefficient[2]
            if count == 0:
                res = torch.cat((res, global_tmp.view(1, -1)), dim=0)
            else:
                res = torch.cat((res, (global_tmp / count).view(1, -1)), dim=0)
        res = res.to("cpu")
        res = self.final_Linear(res)
        res = self.sigmoid(res)
        return res

    def message(self, x_j: Tensor) -> Tensor:
        pass

    def aggregate(self, inputs: Tensor, index: Tensor,
                  ptr: Optional[Tensor] = None,
                  dim_size: Optional[int] = None) -> Tensor:
        pass

    def update(self, inputs: Tensor) -> Tensor:
        pass

    def message_and_aggregate(self, adj_t: SparseTensor) -> Tensor:
        pass

    def edge_update(self) -> Tensor:
        pass


def load_model_to_predict_contract():
    # 挑选出最优秀的模型
    max_score = 0
    print(config.model_data_dir)
    max_mode_file = os.listdir(config.model_data_dir)[0]
    for model_file in os.listdir(config.model_data_dir):
        score = float(model_file.replace(".pth", "").split("_")[3])
        if score > max_score:
            max_score = score
            max_mode_file = model_file
    import datetime
    b1 = datetime.datetime.now()
    model = contract_classification_model_for_predict()
    # 加载原始保存的参数
    model_params_dict = torch.load(os.path.join(config.model_data_dir, max_mode_file))
    best_threshold = model_params_dict["best_threshold"]
    # 将加载的参数添加到模型当中去
    model.load_state_dict(model_params_dict["model_params"])
    # 加载词向量的模型,在这里加载是为了服务所有需要被检验的文件。
    word2vec_model = Word2Vec.load(config.corpus_file_path).wv
    dangerous_count = 0
    safe_count = 0
    exception_count = 0
    detect_res = f"{config.wait_predict_fold}/res_contract.json"
    res_list = []
    if os.path.exists(detect_res):  # 如果文件存在，读取一下
        with open(detect_res, 'r') as res:
            res_list = json.load(res)
    e1 = datetime.datetime.now()
    utils.tip(f"加载模型一共耗时:{e1 - b1}")
    # 遍历wait_pre下的
    for project_name in tqdm(os.listdir(config.wait_predict_sol_source_fold)):
        if not project_name == config.target_dir:
            continue
        # wait_predict/sol_source/下面所有的工程文件夹
        sol_source_project_dir_path = f'{config.wait_predict_sol_source_fold}/{project_name}'
        ast_json_project_dir_path = f'{config.wait_predict_ast_json_fold}/{project_name}'
        import datetime
        begin1 = datetime.datetime.now()
        # 删除源文件中的注释
        remove_comments(data_sol_source_project_dir_path=sol_source_project_dir_path)
        # 编译sol_source下工程文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
        compile_files(data_sol_source_project_dir_path=sol_source_project_dir_path,
                      data_ast_json_project_dir_path=ast_json_project_dir_path)
        # 遍历这个json文件的文件夹，取出其中所有的子文件夹
        for now_dir, child_dirs, child_files in os.walk(ast_json_project_dir_path):
            if not now_dir.endswith(config.target_dir):
                continue
            # 遍历工程项目中的每一个文件
            for ast_json_file_name in child_files:
                if not ast_json_file_name == config.target_file.replace(".sol", ".json"):
                    continue
                try:
                    # 读取刚刚记录下来的抽象语法树的json文件
                    project_node_list, project_node_dict = read_compile(now_dir=now_dir,
                                                                        ast_json_file_name=ast_json_file_name)
                    # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
                    append_method_message_by_dict(project_node_dict=project_node_dict,
                                                  file_name=f"{now_dir}/{ast_json_file_name}")
                    # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
                    append_control_flow_information(project_node_list=project_node_list,
                                                    project_node_dict=project_node_dict,
                                                    file_name=f"{now_dir}/{ast_json_file_name}")
                    # 根据内存中的数据，设定图的数据流。
                    append_data_flow_information(project_node_list=project_node_list,
                                                 project_node_dict=project_node_dict,
                                                 file_name=f"{now_dir}/{ast_json_file_name}")
                    try:
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list,
                                             file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)

                        from built_vector_dataset import create_node_feature_json, create_ast_edge_json, \
                            create_cfg_edge_json, create_dfg_edge_json, \
                            create_node_feature_json_by_contract_classification
                        file_name = now_dir + "/" + ast_json_file_name
                        # 对应的raw文件夹路径，因为传入的是AST_json中的部分，所以需要转化为raw的部分。
                        raw_project_dir_path = os.path.dirname(file_name).replace("AST_json", "raw")
                        # 文件夹里面文件的全路径，但是不包含拓展名。这里映射到了raw文件夹中，是为了待会用来创建三个基本文件。
                        raw_project_dir_half_name = file_name.replace("AST_json", "raw").replace(".json", "")

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
                        create_node_feature_json_by_contract_classification(project_node_list,
                                                                            raw_project_dir_half_name,
                                                                            id_mapping_id, word2vec_model)
                        # 传入所有的节点信息，生成抽象语法树的边文件。
                        create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成控制流边的边文件。
                        create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成数据流边的边文件。
                        create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        utils.success(f"{file_name}节点和边文件已经构建完毕。")
                        end1 = datetime.datetime.now()
                        utils.tip(f"构建基础文件一共耗时:{end1 - begin1}")

                    except Exception as e:
                        utils.error(f"{e}需要先更新词表")
                        # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
                        built_corpus_bfs(project_node_list=project_node_list,
                                         file_name=f"{now_dir}/{ast_json_file_name}")
                        built_corpus_dfs(project_node_list=project_node_list,
                                         file_name=f"{now_dir}/{ast_json_file_name}")
                        # 加载词向量的模型,在这里加载是因为原始的文本库模型文件可能被修改了，但是读入的是原始的。
                        word2vec_model = Word2Vec.load(config.corpus_file_path).wv
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list,
                                             file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)

                        # 因为词表缺失，所以重新构建数据集
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list,
                                             file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)

                        from built_vector_dataset import create_node_feature_json, create_ast_edge_json, \
                            create_cfg_edge_json, create_dfg_edge_json, \
                            create_node_feature_json_by_contract_classification
                        file_name = now_dir + "/" + ast_json_file_name
                        # 对应的raw文件夹路径，因为传入的是AST_json中的部分，所以需要转化为raw的部分。
                        raw_project_dir_path = os.path.dirname(file_name).replace("AST_json", "raw")
                        # 文件夹里面文件的全路径，但是不包含拓展名。这里映射到了raw文件夹中，是为了待会用来创建三个基本文件。
                        raw_project_dir_half_name = file_name.replace("AST_json", "raw").replace(".json", "")

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
                        create_node_feature_json_by_contract_classification(project_node_list,
                                                                            raw_project_dir_half_name,
                                                                            id_mapping_id, word2vec_model)
                        # 传入所有的节点信息，生成抽象语法树的边文件。
                        create_ast_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成控制流边的边文件。
                        create_cfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        # 传入所有的节点信息，生成数据流边的边文件。
                        create_dfg_edge_json(project_node_list, raw_project_dir_half_name, id_mapping_id)
                        utils.success(f"{file_name}节点和边文件已经构建完毕。")
                        end1 = datetime.datetime.now()
                        utils.tip(f"构建基础文件一共耗时:{end1 - begin1}")
                    # 打印树的样子。
                    generate_svg(project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")

                    # 获取对应raw工程文件夹下的原始文件名_node.json文件中的内容。
                    node_feature = contract_classification_dataset.get_x(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "node_feature")
                    contract_buggy_record = contract_classification_dataset.get_contract_buggy_record(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    contract_classification_label = contract_classification_dataset.get_x(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "contract_label")
                    owner_file = contract_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_file")
                    owner_contract = contract_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_contract")
                    owner_function = contract_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_function")
                    owner_line = contract_classification_dataset.get_attribute(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")),
                        "owner_line")
                    # 获取抽象语法树边的信息
                    ast_edge_index = contract_classification_dataset.get_ast_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    # 创建边的属性
                    ast_edge_attr = torch.zeros(ast_edge_index.shape[1])
                    cfg_edge_index = contract_classification_dataset.get_cfg_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    cfg_edge_attr = torch.zeros(cfg_edge_index.shape[1]) + 1
                    dfg_edge_index = contract_classification_dataset.get_dfg_edge(
                        os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    dfg_edge_attr = torch.zeros(dfg_edge_index.shape[1]) + 2
                    # 将上面三份内容一起使用，用来构造一份数据集。
                    edge_index = torch.cat((ast_edge_index, cfg_edge_index, dfg_edge_index), dim=1)
                    edge_attr = torch.cat((ast_edge_attr, cfg_edge_attr, dfg_edge_attr))
                    # 通过节点属性，边连接情况，边的属性，还有标签一起构建数据集。
                    predict_data = Data(x=node_feature,  # 节点特征
                                        edge_index=edge_index,  # 是一个[2, num(E)]的矩阵，代表边的连接情况。
                                        edge_attr=edge_attr,  # 象征每一条边分别是0，1，2用来代表原始边，控制流边，数据流边。
                                        conrtract_classification_label=contract_classification_label,
                                        # 每一个节点都有一个对应的合约标签
                                        owner_file=owner_file,  # 当前所属文件
                                        owner_contract=owner_contract,  # 当前节点所属合约
                                        owner_function=owner_function,  # 当前节点所属函数
                                        owner_line=owner_line,  # 当前节点所属行
                                        contract_buggy_record=contract_buggy_record)  # 记录当前对应的file中所有的contract，哪些是包含漏洞的，哪些又是安全的。

                    predict = model(predict_data)
                    if predict.item() >= best_threshold:
                        res_list.append(
                            {
                                "name": f"{file_name.replace('AST_json', 'sol_source').replace('.json', '.sol')}",
                                "label": 1,
                                "attack_type": config.attack_type_name
                            }
                        )
                        utils.error(f"{ast_json_file_name}中存在{config.attack_type_name}类型的漏洞")
                    else:
                        res_list.append(
                            {
                                "name": f"{file_name.replace('AST_json', 'sol_source').replace('.json', '.sol')}",
                                "label": 0,
                                "attack_type": config.attack_type_name
                             }
                        )
                        utils.tip(f"{ast_json_file_name}中不存在{config.attack_type_name}类型的漏洞")
                except Exception as e:
                    utils.success(f"{ast_json_file_name}执行过程中出现异常了{e}")
                    exception_count += 1
    # 准备将这个对象保存为json文件
    utils.save_json(res_list, f"{config.wait_predict_fold}/res_contract.json")


class contract_classification_model_for_predict(MessagePassing):
    def __init__(self):
        super(contract_classification_model_for_predict, self).__init__()
        self.RGCNconv1 = RGCNConv(in_channels=300, out_channels=64, num_relations=3)
        self.RGCNconv2 = RGCNConv(in_channels=64, out_channels=32, num_relations=3)
        self.RGCNconv3 = RGCNConv(in_channels=32, out_channels=16, num_relations=3)
        self.RGCNconv4 = RGCNConv(in_channels=16, out_channels=8, num_relations=3)
        self.final_Linear = Linear(in_channels=8, out_channels=1)
        self.dropout = Dropout(p=config.dropout_pro)
        self.relu = ReLU()
        self.sigmoid = Sigmoid()

    def forward(self, data):
        x = self.RGCNconv1(data.x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv2(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv3(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = self.RGCNconv4(x, data.edge_index, data.edge_attr)
        x = self.dropout(x)
        x = self.relu(x)
        x = x.to(config.device)
        # 在这里根据合约的包含范围，对batch进行操作，然后找到需要返回的结果，同时需要用线性层继续学习一下。
        res = torch.tensor([]).to(config.device)
        # 依次循环遍历每一种contract
        for contract_name in data.contract_buggy_record:
            global_tmp = torch.zeros(x[0].shape).to(config.device)
            count = 0
            # 针对当前遍历的contract找出所有对应的节点
            for index, ite in enumerate(data.owner_contract):
                # 如果名字匹配，那么index就说明找到目标节点了。
                if ite == contract_name:
                    global_tmp += x[index]
                    count += 1
            res = torch.cat((res, (global_tmp / count).view(1, -1)), dim=0)
        real_res = torch.zeros(8).to(config.device)
        for r in res:
            real_res += r
        real_res = real_res.to("cpu")
        real_res = real_res / len(data.contract_buggy_record)
        real_res = self.final_Linear(real_res)
        real_res = self.sigmoid(real_res)
        return real_res

    def message(self, x_j: Tensor) -> Tensor:
        pass

    def aggregate(self, inputs: Tensor, index: Tensor,
                  ptr: Optional[Tensor] = None,
                  dim_size: Optional[int] = None) -> Tensor:
        pass

    def update(self, inputs: Tensor) -> Tensor:
        pass

    def message_and_aggregate(self, adj_t: SparseTensor) -> Tensor:
        pass

    def edge_update(self) -> Tensor:
        pass
