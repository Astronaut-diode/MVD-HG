# coding=UTF-8
from torch_geometric.nn import MessagePassing, global_mean_pool, Linear, RGCNConv, RGATConv, GATConv
from typing import Optional
from torch import Tensor
from torch.nn import ReLU, Sigmoid, Dropout
from torch_sparse import SparseTensor
import config
import torch


class line_classification_model(MessagePassing):
    def __init__(self):
        super(line_classification_model, self).__init__()
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

        # 在这里根据合约的包含范围，对batch进行操作，然后找到需要返回的结果，同时需要用线性层继续学习一下。
        res = torch.tensor([]).to(config.device)
        stand = torch.tensor(data.contract_buggy_line[0]).to(config.device)
        # 依次循环遍历每一种contract
        for line in range(len(data.contract_buggy_line[0])):
            global_tmp = torch.zeros(x[0].shape).to(config.device)
            count = 0
            # 针对当前遍历的行号+1找出所有对应的节点
            for index, ite in enumerate(data.owner_line[0]):
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
        res = self.final_Linear(res)
        res = self.sigmoid(res)
        return res, stand

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
