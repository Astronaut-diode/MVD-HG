# coding=UTF-8
from torch_geometric.nn import MessagePassing, GATConv, global_mean_pool, Linear
from typing import Optional
from torch import Tensor
from torch.nn import ReLU
import config


class ASTGNNModel(MessagePassing):
    def __init__(self):
        super(ASTGNNModel, self).__init__()
        self.GATconv = GATConv(128, 1)
        self.Linear = Linear(in_channels=1, out_channels=config.classes)
        self.relu = ReLU()

    def forward(self, x, edge_index, batch):
        x = self.GATconv(x, edge_index)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=batch)
        x = self.Linear(x)
        return x

    def message(self, x_j: Tensor) -> Tensor:
        pass

    def aggregate(self, inputs: Tensor, index: Tensor,
                  ptr: Optional[Tensor] = None,
                  dim_size: Optional[int] = None) -> Tensor:
        pass

    def update(self, inputs: Tensor) -> Tensor:
        pass
