# coding=UTF-8
from torch_geometric.nn import MessagePassing, GATConv, global_mean_pool, Linear, RGCNConv
from typing import Optional
from torch import Tensor
from torch.nn import ReLU
from torch_sparse import SparseTensor

import config


class ASTGNNModel(MessagePassing):
    def __init__(self):
        super(ASTGNNModel, self).__init__()
        self.GATconv_AST = GATConv(128, 256)
        self.GATconv_CFG = GATConv(128, 256)
        self.GATconv_DFG = GATConv(128, 256)
        self.GATconv_AST1 = GATConv(256, 1)
        self.GATconv_CFG1 = GATConv(256, 1)
        self.GATconv_DFG1 = GATConv(256, 1)
        self.Linear_AST = Linear(in_channels=1, out_channels=config.classes)
        self.Linear_CFG = Linear(in_channels=1, out_channels=config.classes)
        self.Linear_DFG = Linear(in_channels=1, out_channels=config.classes)
        self.final_Linear = Linear(in_channels=2 * config.classes, out_channels=config.classes)
        self.relu = ReLU()

    def forward(self, ast_x, ast_edge_index, ast_batch, cfg_x, cfg_edge_index, cfg_batch, dfg_x, dfg_edge_index, dfg_batch):
        # 分别计算出两个结果
        ast_x = self.ast_forward(ast_x, ast_edge_index, ast_batch)
        cfg_x = self.cfg_forward(cfg_x, cfg_edge_index, cfg_batch)
        dfg_x = self.dfg_forward(dfg_x, dfg_edge_index, dfg_batch)
        # 方式1，两个都采用0.5倍数
        out = (ast_x + cfg_x + dfg_x) * 0.5
        # 对两者的结果进行结合，然后返回结果。对他们cat以后使用全连接计算。
        # out = torch.cat((ast_x, cfg_x), dim=1)
        # 从双类别，合并为单类别。
        # out = self.final_Linear(out)
        return out

    # 传入单组数据，然后计算出结果，这是抽象语法树的部分。
    def ast_forward(self, x, edge_index, batch):
        x = self.GATconv_AST(x, edge_index)
        x = self.GATconv_AST1(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear_AST(x)
        return x

    # 传入单组数据，然后计算出结果，这是控制流图的部分。
    def cfg_forward(self, x, edge_index, batch):
        x = self.GATconv_CFG(x, edge_index)
        x = self.GATconv_CFG1(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear_CFG(x)
        return x

    # 传入单组数据，然后计算出结果，这是控制流图的部分。
    def dfg_forward(self, x, edge_index, batch):
        x = self.GATconv_DFG(x, edge_index)
        x = self.GATconv_DFG1(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear_DFG(x)
        return x

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
