# coding=UTF-8
from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch_geometric.loader import DataLoader
from metric import metric
from torch.utils.tensorboard import SummaryWriter
import torch
import config

device = torch.device(config.device)
writer = SummaryWriter(config.tensor_board_position)


def train():
    # 获取训练用的数据集。
    dataset = ASTGNNDataset(config.data_dir_path)
    # 将数据集加载到loader当中。别用shuffle，用了shuffle这两个数据集打乱的顺序就不一样了，不方便一起循环，不方便和zip一起使用。
    data_loader = DataLoader(dataset=dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    model = ASTGNNModel()
    # 将模型转化为在指定设备上运行的类型。
    model = model.to(device)
    # 创建优化器和反向传播函数。
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = torch.nn.BCEWithLogitsLoss()
    # 进行epoch个时代的训练
    model.train()
    count = 0
    for epoch in range(config.epoch_size):
        for index, batch in enumerate(data_loader):
            # 将数据转化为指定设备上运行
            batch = batch.to(device)
            # 经典的五步计算
            optimizer.zero_grad()
            # 将两个batch的节点，边还有batch信息都传进去
            predict = model(batch.x, batch.edge_index[0], batch.batch, batch.x, batch.edge_index[1], batch.batch, batch.x, batch.edge_index[2], batch.batch)
            # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
            loss = criterion(predict, batch.y)
            loss.backward()
            optimizer.step()
            # 进行准确率计算。
            print(f"epoch:{epoch}, index:{index}, 当前阶段的loss为{loss}", end="")
            writer.add_scalar("train_loss", loss, count)
            metric(predict, batch.y, count, writer)
            count = count + 1
    writer.close()
