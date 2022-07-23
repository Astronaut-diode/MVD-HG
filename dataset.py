# coding=UTF-8
from typing import Tuple, Union, List
from torch_geometric.data import Data, Dataset
import numpy as np
import torch
import json
import os
import config
import utils


class ASTGNNDataset(Dataset):
    def __init__(self, root_dir):
        super().__init__(root_dir)
        self.data = torch.load(self.processed_file_names[0])

    # 1.先判断原始文件是否已经存在了，如果存在了那就没有关系，否则是需要提醒报错的。
    @property
    def raw_file_names(self) -> Union[str, List[str], Tuple]:
        # 保存原始文件中所有工程文件夹名字的列表
        project_file_list = []
        # 循环raw目录下所有的工程文件夹，获取所有的工程文件夹名字,保存的是全路径。
        for project_name in os.listdir(config.data_raw_dir_path):
            project_dir = os.path.join(config.data_raw_dir_path, project_name)
            project_file_list.append(project_dir)
        return project_file_list

    # 3.获取处理以后文件的名字
    @property
    def processed_file_names(self) -> Union[str, List[str], Tuple]:
        return [f"{self.root}/processed/graph_train.pt"]

    # 2.如果原始文件不存在，说明无法生成数据集。
    def download(self):
        if len(self.raw_file_names) == 0:
            print("原始文件不存在，无法生成数据集。")

    # 4.对文件进行处理，然后保存到processed中返回的文件列表里面去。
    def process(self):
        label_in_memory = utils.get_label()
        # 保存到数据集文件中的容器。
        graph_data_list = []
        for project_full_path in self.raw_file_names:
            # 这里replace成AST_json是因为目前来说只有AST_json里面的文件夹是完整的，sol_source里面已经被删除了。
            for now_dir, child_dirs, child_files in os.walk(project_full_path.replace("raw", "AST_json")):
                for file_name in child_files:
                    file_name_key = f"{now_dir}/{file_name}"
                    # 通过文件的全路径获取其标签。
                    y = torch.as_tensor(data=np.array([label_in_memory[file_name_key]], dtype=np.float64))
                    # 获取对应raw工程文件夹下的原始文件名_node.json文件中的内容。
                    x = self.get_x(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    # 获取抽象语法树边的信息
                    ast_edge_index = self.get_ast_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    cfg_edge_index = self.get_cfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    dfg_edge_index = self.get_dfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), file_name.replace(".json", "")))
                    # 通过x和ast_edge_index一起构造图数据
                    graph_train_data = Data(x=x, edge_index=[ast_edge_index, cfg_edge_index, dfg_edge_index], y=y)
                    # 添加到列表中，待会可以直接一次性保存。
                    graph_data_list.append(graph_train_data)
        # 数据构造完毕以后，直接保存到对应文件中即可。
        torch.save(graph_data_list, self.processed_file_names[0])

    def len(self) -> int:
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]

    # 获取node.json中的节点特征，并排列为[节点个数, 节点特征]的二维数组
    def get_x(self, project):
        # 先获取节点文件的路径
        node_file_path = f"{project}_node.json"
        # 根据路径获取对应的句柄
        node_file_handle = open(node_file_path, 'r')
        # 通过句柄，读取json文件中的内容
        node_content = json.load(node_file_handle)
        x = []
        # 分行读取json中的内容，然后添加到x中
        for index, content in enumerate(node_content):
            x.append(content['node_feature'])
        # 将x转化为torch形式
        x = torch.as_tensor(data=np.array(x, dtype=np.float32))
        # 已经读取完毕，所以需要关闭句柄对象
        node_file_handle.close()
        return x

    # 获取ast_edge.json中的文件内容。
    def get_ast_edge(self, project):
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
    def get_cfg_edge(self, project):
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
    def get_dfg_edge(self, project):
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