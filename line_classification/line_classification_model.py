# coding=UTF-8
from torch_geometric.nn import MessagePassing, GATConv, global_mean_pool, Linear, RGCNConv
from typing import Optional
from torch import Tensor
from torch.nn import ReLU, Sigmoid
from torch_sparse import SparseTensor
import config


class line_classification_model(MessagePassing):
    def __init__(self):
        super(line_classification_model, self).__init__()
        self.RGCNconv1 = RGCNConv(in_channels=300, out_channels=128, num_relations=3)
        self.RGCNconv2 = RGCNConv(in_channels=128, out_channels=64, num_relations=3)
        self.RGCNconv3 = RGCNConv(in_channels=64, out_channels=32, num_relations=3)
        self.RGCNconv4 = RGCNConv(in_channels=32, out_channels=1, num_relations=3)
        self.relu = ReLU()
        self.sigmoid = Sigmoid()

    def forward(self, data):
        x = self.RGCNconv1(data.x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = self.RGCNconv2(x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = self.RGCNconv3(x, data.edge_index, data.edge_attr)
        x = self.relu(x)
        x = self.RGCNconv4(x, data.edge_index, data.edge_attr)
        x = self.sigmoid(x)
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
