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
        self.RGCNconv1 = RGCNConv(in_channels=300, out_channels=64, num_relations=3)
        self.RGCNconv2 = RGCNConv(in_channels=64, out_channels=32, num_relations=3)
        self.RGCNconv3 = RGCNConv(in_channels=32, out_channels=16, num_relations=3)
        self.final_Linear = Linear(in_channels=16, out_channels=1)
        self.relu = ReLU()

    def forward(self, data):
        x = self.RGCNconv1(data.x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = self.RGCNconv2(x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = self.RGCNconv3(x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = global_mean_pool(x=x, batch=data.batch)
        x = self.final_Linear(x)
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
