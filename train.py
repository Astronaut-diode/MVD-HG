# coding=UTF-8
from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch_geometric.loader import DataLoader
import os
import torch
import config

device = torch.device(config.device)


def train():
    # 获取训练用的数据集。
    dataset = ASTGNNDataset(config.data_dir_path)
    # 将数据集加载到loader当中。别用shuffle，用了shuffle这两个数据集打乱的顺序就不一样了，不方便一起循环，不方便和zip一起使用。
    data_loader = DataLoader(dataset=dataset, batch_size=config.batch_size, shuffle=False, drop_last=False)
    model = ASTGNNModel()
    # 将模型转化为在指定设备上运行的类型。
    model = model.to(device)
    # 创建优化器和反向传播函数。
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = torch.nn.CrossEntropyLoss()
    # 进行epoch个时代的训练
    model.train()
    for epoch in range(config.epoch_size):
        train_correct = 0
        train_total = 0
        # 使用zip对他们两个进行并行循环，因为长度是一样的，所以完全可以使用。
        for index, batch in enumerate(data_loader):
            # 将数据转化为指定设备上运行
            batch = batch.to(device)
            # 经典的五步计算
            optimizer.zero_grad()
            # 将两个batch的节点，边还有batch信息都传进去
            output = model(batch.x, batch.edge_index[0], batch.batch, batch.x, batch.edge_index[1], batch.batch, batch.x, batch.edge_index[2], batch.batch)
            # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
            loss = criterion(output, batch.y)
            loss.backward()
            optimizer.step()
            # 进行准确率计算。
            pred = output.argmax(dim=1)
            train_correct = train_correct + (pred == batch.y.argmax(dim=1)).sum()
            train_total = train_total + batch.num_graphs
            print("\r", epoch, index, "当前阶段的loss为{:.4f}, 正确率为{:.2f}%".format(loss, (train_correct / train_total) * 100),
                  end="")
