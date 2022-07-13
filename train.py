from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch_geometric.data import DataLoader
import os
import torch
import config

parent_path = os.getcwd()
data_path = f'{parent_path}/data/'
device = torch.device(config.device)


def train():
    # 获取训练用的数据集。
    dataset = ASTGNNDataset(data_path, "AST")
    # 将数据集加载到loader当中。
    data_loader = DataLoader(dataset=dataset, batch_size=64, shuffle=True, drop_last=False)
    model = ASTGNNModel()
    # 将模型转化为在指定设备上运行的类型。
    model = model.to(device)
    # 创建优化器和反向传播函数。
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
    criterion = torch.nn.CrossEntropyLoss()
    # 进行epoch个时代的训练
    model.train()
    for epoch in range(10):
        train_correct = 0
        train_total = 0
        for index, batch in enumerate(data_loader):
            batch = batch.to(device)
            optimizer.zero_grad()
            output = model(batch.x, batch.edge_index, batch.batch)
            loss = criterion(output, batch.y)
            loss.backward()
            optimizer.step()
            # 计算训练阶段的正确率
            pred = output.argmax(dim=1)
            train_correct = train_correct + (pred == batch.y).sum()
            train_total = train_total + batch.num_graphs
            print("\r", epoch, index, "当前阶段的loss为{:.4f}, 正确率为{:.2f}%".format(loss, (train_correct / train_total) * 100),
                  end="")
