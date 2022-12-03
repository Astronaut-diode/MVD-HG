from typing import Tuple, Union, List
from torch_geometric.data import Data, Dataset
import numpy as np
import torch
import json
import os
import config
import utils
import random


# 用于行级别分类检测的数据集。
class line_classification_dataset(Dataset):
    def __init__(self, root_dir):
        super().__init__(root_dir)
        self.data = torch.load(self.processed_file_names[0])
        random.shuffle(self.data)

    # 1.先判断原始文件是否已经存在了，如果存在了那就没有关系，否则是需要提醒报错的。
    # 这里指的原始文件是那几个使用built_vector_dataset创建的json文件。
    @property
    def raw_file_names(self) -> Union[str, List[str], Tuple]:
        # 保存原始文件中所有工程文件夹名字的列表
        project_file_list = []
        # 循环raw目录下所有的工程文件夹，获取所有的工程文件夹名字,保存的是全路径。
        for project_name in os.listdir(config.data_raw_dir_path):
            project_dir = os.path.join(config.data_raw_dir_path, project_name)
            project_file_list.append(project_dir)
        return project_file_list

    # 2.如果原始文件不存在，说明无法生成数据集。
    def download(self):
        if len(self.raw_file_names) == 0:
            utils.error("原始文件不存在，无法生成数据集。")

    # 3.获取处理以后文件的名字
    @property
    def processed_file_names(self) -> Union[str, List[str], Tuple]:
        # 保存文件为指定的名字。
        return [f"{self.root}/processed/{config.attack_type_name}.pt"]

    # 4.对文件进行处理，然后保存到processed中返回的文件列表里面去。
    def process(self):
        # 保存到数据集文件中的容器。
        data_list = []
        for project_full_path in self.raw_file_names:
            # 这里replace成AST_json是因为目前来说只有AST_json里面的文件夹是完整的，sol_source里面已经被删除了。
            for now_dir, child_dirs, child_files in os.walk(project_full_path.replace("raw", "AST_json")):
                for file_name in child_files:
                    # 获取对应raw工程文件夹下的原始文件名_node.json文件中的内容。
                    node_feature = self.get_x(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "node_feature")
                    # 智能合约文件中所有包含漏洞的代码行
                    contract_buggy_line = self.get_contract_buggy_line(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    # 文件中当前所在contract的分类标签
                    contract_classification_label = self.get_x(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "contract_label")
                    # 文件中当前所在行的分类标签
                    line_classification_label = self.get_x(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "line_label")
                    # 当前行所处在的四种位置。
                    owner_file = self.get_attribute(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "owner_file")
                    owner_contract = self.get_attribute(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "owner_contract")
                    owner_function = self.get_attribute(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "owner_function")
                    owner_line = self.get_attribute(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")), "owner_line")
                    # 获取抽象语法树边的信息
                    ast_edge_index = self.get_ast_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    # 创建边的属性
                    ast_edge_attr = torch.zeros(ast_edge_index.shape[1])
                    cfg_edge_index = self.get_cfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    cfg_edge_attr = torch.zeros(cfg_edge_index.shape[1]) + 1
                    dfg_edge_index = self.get_dfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    dfg_edge_attr = torch.zeros(dfg_edge_index.shape[1]) + 2
                    # 将上面三份内容一起使用，用来构造一份数据集。
                    edge_index = torch.cat((ast_edge_index, cfg_edge_index, dfg_edge_index), dim=1)
                    edge_attr = torch.cat((ast_edge_attr, cfg_edge_attr, dfg_edge_attr))
                    # 通过节点属性，边连接情况，边的属性，还有标签一起构建数据集。
                    data = Data(x=node_feature,  # 节点特征
                                edge_index=edge_index,  # 是一个[2, num(E)]的矩阵，代表边的连接情况。
                                edge_attr=edge_attr,  # 象征每一条边分别是0，1，2用来代表原始边，控制流边，数据流边。
                                conrtract_classification_label=contract_classification_label,  # 每一个节点都有一个对应的合约标签
                                line_classification_label=line_classification_label,  # 行标签
                                owner_file=owner_file,  # 当前所属文件
                                owner_contract=owner_contract,  # 当前节点所属合约
                                owner_function=owner_function,  # 当前节点所属函数
                                owner_line=owner_line,  # 当前节点所属行
                                contract_buggy_line=contract_buggy_line)  # 当前节点对应的文件中所有的行，如果该行没有漏洞，那么值就是0，否则是1
                    data_list.append(data)
        # 数据构造完毕以后，直接保存到对应文件中即可。
        torch.save(data_list, self.processed_file_names[0])

    def len(self) -> int:
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]

    # 这个方法是用来获取节点所属的文件、合约、函数、行情况的。
    @staticmethod
    def get_attribute(project, attribute):
        # 先获取节点文件的路径
        node_file_path = f"{project}_node.json"
        # 根据路径获取对应的句柄
        node_file_handle = open(node_file_path, 'r')
        # 通过句柄，读取json文件中的内容
        node_content = json.load(node_file_handle)
        x = []
        # 分行读取json中的内容，然后添加到x中
        for index, content in enumerate(node_content["node_feature_list"]):
            x.append(content[attribute])
        # 已经读取完毕，所以需要关闭句柄对象
        node_file_handle.close()
        return x

    # 这个方法是用来获取节点所属的文件、合约、函数、行情况的。
    @staticmethod
    def get_contract_buggy_line(project):
        # 先获取节点文件的路径
        node_file_path = f"{project}_node.json"
        # 根据路径获取对应的句柄
        node_file_handle = open(node_file_path, 'r')
        # 通过句柄，读取json文件中的内容
        node_content = json.load(node_file_handle)
        x = node_content["contract_buggy_line"]
        # 已经读取完毕，所以需要关闭句柄对象
        node_file_handle.close()
        return x

    # 获取node.json中的节点特征，并排列为[节点个数, 节点特征]的二维数组
    # 这个方法是用来获取node文件当中的节点特征，节点的行标签以及合约标签的。
    @staticmethod
    def get_x(project, label):
        # 先获取节点文件的路径
        node_file_path = f"{project}_node.json"
        # 根据路径获取对应的句柄
        node_file_handle = open(node_file_path, 'r')
        # 通过句柄，读取json文件中的内容
        node_content = json.load(node_file_handle)
        x = []
        # 分行读取json中的内容，然后添加到x中
        for index, content in enumerate(node_content["node_feature_list"]):
            x.append(content[label])
        # 将x转化为torch形式
        x = torch.as_tensor(data=np.array(x, dtype=np.float32))
        # 已经读取完毕，所以需要关闭句柄对象
        node_file_handle.close()
        return x

    # 获取ast_edge.json中的文件内容。
    @staticmethod
    def get_ast_edge(project):
        ast_edge_file_path = f"{project}_ast_edge.json"
        ast_edge_file_handle = open(ast_edge_file_path, 'r')
        ast_edge_content = json.load(ast_edge_file_handle)
        ast_edge_index = []
        for index, content in enumerate(ast_edge_content):
            # 因为一开始写在json里面的时候是从1开始计算的，但是如果送到模型里面，需要从0开始。
            ast_edge_index.append([content['source_node_node_id'] - 1, content['target_node_node_id'] - 1])
        ast_edge_index = torch.as_tensor(data=np.array(ast_edge_index, dtype=np.int64))
        ast_edge_file_handle.close()
        return ast_edge_index.T

    # 获取cfg_edge.json中的文件内容。
    @staticmethod
    def get_cfg_edge(project):
        cfg_edge_file_path = f"{project}_cfg_edge.json"
        cfg_edge_file_handle = open(cfg_edge_file_path, 'r')
        cfg_edge_content = json.load(cfg_edge_file_handle)
        cfg_edge_index = []
        for index, content in enumerate(cfg_edge_content):
            # 因为一开始写在json里面的时候是从1开始计算的，但是如果送到模型里面，需要从0开始。
            cfg_edge_index.append([content['source_node_node_id'] - 1, content['target_node_node_id'] - 1])
        cfg_edge_index = torch.as_tensor(data=np.array(cfg_edge_index, dtype=np.int64))
        cfg_edge_file_handle.close()
        return cfg_edge_index.T

    # 获取dfg_edge.json中的文件内容。
    @staticmethod
    def get_dfg_edge(project):
        dfg_edge_file_path = f"{project}_dfg_edge.json"
        dfg_edge_file_handle = open(dfg_edge_file_path, 'r')
        dfg_edge_content = json.load(dfg_edge_file_handle)
        dfg_edge_index = []
        for index, content in enumerate(dfg_edge_content):
            # 因为一开始写在json里面的时候是从1开始计算的，但是如果送到模型里面，需要从0开始。
            dfg_edge_index.append([content['source_node_node_id'] - 1, content['target_node_node_id'] - 1])
        dfg_edge_index = torch.as_tensor(data=np.array(dfg_edge_index, dtype=np.int64))
        dfg_edge_file_handle.close()
        return dfg_edge_index.T

    def get(self, idx: int) -> Data:
        return self.data[idx]
