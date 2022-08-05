# coding=UTF-8
from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch_geometric.loader import DataLoader
from metric import score
from torch.utils.tensorboard import SummaryWriter
from sklearn.model_selection import KFold
from tqdm import tqdm
import datetime
import utils
import torch
import config
import sys

device = torch.device(config.device)
writer = SummaryWriter(config.tensor_board_position)


def train():
    # 获取训练用的数据集。
    dataset = ASTGNNDataset(config.data_dir_path)
    # 定义 K 折交叉验证
    k_fold = KFold(n_splits=config.k_folds, shuffle=True)
    # K折交叉验证模型评估
    for fold, (train_ids, test_ids) in enumerate(tqdm(k_fold.split(dataset), desc="K-FOLD", leave=False, file=sys.stdout)):
        # 获取K折以后的train和test数据集
        train_dataset = torch.utils.data.dataset.Subset(dataset, train_ids)
        test_dataset = torch.utils.data.dataset.Subset(dataset, test_ids)
        # 将数据集加载到loader当中。
        train_dataloader = DataLoader(dataset=train_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
        test_dataloader = DataLoader(dataset=test_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
        # 加载网络，这里是为了避免使用同一个网络，对于不同的K折交叉验证会有影响。
        model = ASTGNNModel()
        # 将模型转化为在指定设备上运行的类型。
        model = model.to(device)
        # 创建优化器和反向传播函数。
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
        criterion = torch.nn.BCEWithLogitsLoss()
        # 进行Epoch次的训练，由config配置文件中指定。
        for epoch in tqdm(range(config.epoch_size), desc=f"K-Fold{fold}===>Epoch", leave=False, ncols=config.tqdm_ncols, file=sys.stdout):
            # 保存当前的epoch所记录的所有答案。
            train_all_predicts = torch.tensor([]).to(device)
            train_all_labels = torch.tensor([]).to(device)
            test_all_predicts = torch.tensor([]).to(device)
            test_all_labels = torch.tensor([]).to(device)
            train_total_loss = 0.0
            test_total_loss = 0.0
            # 开始训练的信号,进行训练集上的计算
            model.train()
            for train_batch in tqdm(train_dataloader, desc=f"Epoch {epoch}===>Train", leave=False, postfix=f"{train_total_loss}", ncols=config.tqdm_ncols, file=sys.stdout):
                # 将数据转化为指定设备上运行
                train_batch = train_batch.to(device)
                # 经典的五步计算
                optimizer.zero_grad()
                # 将两个batch的节点，边还有batch信息都传进去
                predict = model(train_batch.x, train_batch.edge_index[0], train_batch.batch, train_batch.x, train_batch.edge_index[1], train_batch.batch, train_batch.x, train_batch.edge_index[2], train_batch.batch)
                # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
                loss = criterion(predict, train_batch.y)
                loss.backward()
                optimizer.step()
                # 计算训练集上总的损失值
                train_total_loss += loss.item()
                # 保存其中每一个mini batch计算出的结果与对应的标签。
                train_all_predicts = torch.cat((train_all_predicts, predict), dim=0)
                train_all_labels = torch.cat((train_all_labels, train_batch.y), dim=0)
            # 计算对应的度量标准，进行阈值调优。
            score(train_all_predicts, train_all_labels, writer, fold, epoch)
            model.eval()
            for test_batch in tqdm(test_dataloader, desc=f"Epoch {epoch}===> Test", leave=False, ncols=config.tqdm_ncols, file=sys.stdout):
                # 将数据转化为指定设备上运行
                test_batch = test_batch.to(device)
                # 经典的五步计算
                optimizer.zero_grad()
                # 将两个batch的节点，边还有batch信息都传进去
                predict = model(test_batch.x, test_batch.edge_index[0], test_batch.batch, test_batch.x, test_batch.edge_index[1], test_batch.batch, test_batch.x, test_batch.edge_index[2], test_batch.batch)
                # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
                loss = criterion(predict, test_batch.y)
                # 计算验证集上的总损失值
                test_total_loss += loss.item()
                # 保存其中每一个mini batch计算出的结果与对应的标签。
                test_all_predicts = torch.cat((test_all_predicts, predict), dim=0)
                test_all_labels = torch.cat((test_all_labels, test_batch.y), dim=0)
            # 计算对应的度量标准，进行阈值调优。
            score(test_all_predicts, test_all_labels, writer, fold, epoch)
            # 计算对应的度量标准，进行阈值调优。
            utils.tqdm_write(f"第{fold}折中第{epoch}个epoch中训练集计算出来的loss为{train_total_loss / len(train_dataloader)}")
            utils.tqdm_write(f"第{fold}折中第{epoch}个epoch中测试集计算出来的loss为{test_total_loss / len(test_dataloader)}")
        # 每一折计算完之后保存一个模型文件
        torch.save({'model_params': model.state_dict()}, f'{config.model_data_dir}/{datetime.datetime.now()}_{fold}.pth')
