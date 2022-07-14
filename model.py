# coding=UTF-8
from torch_geometric.nn import MessagePassing, GATConv, global_mean_pool, Linear
from typing import Optional
from torch import Tensor
from torch.nn import ReLU
import config
import torch


class ASTGNNModel(MessagePassing):
    def __init__(self):
        super(ASTGNNModel, self).__init__()
        self.GATconv = GATConv(128, 1)
        self.GATconv_tmp = GATConv(128, 1)
        self.Linear = Linear(in_channels=1, out_channels=config.classes)
        self.Linear_tmp = Linear(in_channels=1, out_channels=config.classes)
        self.final_Linear = Linear(in_channels=2 * config.classes, out_channels=config.classes)
        self.relu = ReLU()

    def forward(self, ast_x, ast_edge_index, ast_batch, cfg_x, cfg_edge_index, cfg_batch):
        # 分别计算出两个结果
        ast_x = self.ast_forward(ast_x, ast_edge_index, ast_batch)
        cfg_x = self.cfg_forward(cfg_x, cfg_edge_index, cfg_batch)
        # 方式1，两个都采用0.5倍数
        out = (ast_x + cfg_x) * 0.5
        # 对两者的结果进行结合，然后返回结果。对他们cat以后使用全连接计算。
        # out = torch.cat((ast_x, cfg_x), dim=1)
        # 从双类别，合并为单类别。
        # out = self.final_Linear(out)
        return out

    # 传入单组数据，然后计算出结果，这是抽象语法树的部分。
    def ast_forward(self, x, edge_index, batch):
        x = self.GATconv(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear(x)
        return x

    # 传入单组数据，然后计算出结果，这是控制流图的部分。
    def cfg_forward(self, x, edge_index, batch):
        x = self.GATconv_tmp(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear_tmp(x)
        return x

    def message(self, x_j: Tensor) -> Tensor:
        pass

    def aggregate(self, inputs: Tensor, index: Tensor,
                  ptr: Optional[Tensor] = None,
                  dim_size: Optional[int] = None) -> Tensor:
        pass

    def update(self, inputs: Tensor) -> Tensor:
        pass
