# coding=UTF-8
from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch_geometric.loader import DataLoader
from torch_geometric.data import DataListLoader
from torch_geometric.nn import DataParallel
from metric import test_score, valid_score
from torch.utils.tensorboard import SummaryWriter
from sklearn.model_selection import KFold
from tqdm import tqdm
import numpy as np
import utils
import datetime
import torch
import config
import sys

device = torch.device(config.device)
writer = SummaryWriter(config.tensor_board_position)


def train():
    # 分割为训练集和测试集，下面再对训练集进行K折交叉验证的操作。
    origin_train_dataset = ASTGNNDataset(config.data_dir_path, "train")
    test_dataset = ASTGNNDataset(config.data_dir_path, "test")
    test_dataloader = DataListLoader(dataset=test_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
    # 定义 K 折交叉验证
    k_fold = KFold(n_splits=config.k_folds, shuffle=True)
    # 创建精度的集合，是一个3维内容，分别是折，4 * 3相当于每一折的结果都作为一个平面叠加上去。
    metric = torch.zeros((config.k_folds, 4, config.classes))
    # K折交叉验证模型评估，对训练集进行十折划分。
    for fold, (train_ids, valid_ids) in enumerate(tqdm(k_fold.split(origin_train_dataset), desc="K-FOLD", leave=False, file=sys.stdout)):
        # 获取K折以后的train和valid数据集
        train_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, train_ids)
        valid_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, valid_ids)
        # 将数据集加载到loader当中。
        train_dataloader = DataListLoader(dataset=train_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
        valid_dataloader = DataListLoader(dataset=valid_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False)
        # 加载网络，这里是为了避免使用同一个网络，对于不同的K折交叉验证会有影响。
        model = ASTGNNModel()
        model = DataParallel(model.cuda())
        # 将模型转化为在指定设备上运行的类型。
        model = model.to(device)
        # 创建优化器和反向传播函数。
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
        criterion = torch.nn.BCEWithLogitsLoss()
        # 进行Epoch次的训练，由config配置文件中指定。
        for epoch in tqdm(range(config.epoch_size), desc=f"K-Fold{fold}===>Epoch", leave=False, ncols=config.tqdm_ncols, file=sys.stdout):
            # 开始训练的信号,进行训练集上的计算
            model.train()
            train_total_loss = 0.0
            for train_batch in tqdm(train_dataloader, desc=f"Epoch {epoch}===>Train", leave=False, postfix=f"{train_total_loss}", ncols=config.tqdm_ncols, file=sys.stdout):
                # 经典的五步计算
                optimizer.zero_grad()
                # 将两个batch的节点，边还有batch信息都传进去
                predict = model(train_batch)
                # 单独拿出y因为后面要用到
                y = torch.cat([data.y for data in train_batch]).to(predict.device)
                # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
                loss = criterion(predict, y)
                loss.backward()
                optimizer.step()
                # 计算训练集上总的损失值
                train_total_loss += loss.item()
        # 开始验证集上的操作
        model.eval()
        valid_all_predicts = torch.tensor([]).to(device)
        valid_all_labels = torch.tensor([]).to(device)
        valid_total_loss = 0.0
        for valid_batch in tqdm(valid_dataloader, desc=f"Valid", leave=False, ncols=config.tqdm_ncols, file=sys.stdout):
            # 将两个batch的节点，边还有batch信息都传进去
            predict = model(valid_batch)
            # 单独拿出y因为后面要用到
            y = torch.cat([data.y for data in valid_batch]).to(predict.device)
            # 计算准确率计算一次就行了，因为两个人的结果是一样的，而且本来就是两个模型合并起来计算。
            loss = criterion(predict, y)
            # 计算验证集上的总损失值
            valid_total_loss += loss.item()
            # 保存其中每一个mini batch计算出的结果与对应的标签。
            valid_all_predicts = torch.cat((valid_all_predicts, predict), dim=0)
            valid_all_labels = torch.cat((valid_all_labels, y), dim=0)
        # 先是对验证集上的结果进行画图，并打印表格，最终返回最好的阈值。
        config.reentry_threshold, config.timestamp_threshold, config.arithmetic_threshold = valid_score(valid_all_predicts, valid_all_labels, writer, f"{fold}折中Valid的loss{format(valid_total_loss / len(valid_dataloader), '.20f')}")
        # 进行测试集上的操作,创建两个容器，分别记录结果和原始标签。
        test_all_predicts = torch.tensor([]).to(device)
        test_all_labels = torch.tensor([]).to(device)
        test_total_loss = 0.0
        for test_batch in tqdm(test_dataloader, desc=f"Test", leave=False, ncols=config.tqdm_ncols, file=sys.stdout):
            # 将两个batch的节点，边还有batch信息都传进去
            predict = model(test_batch)
            # 单独拿出y因为后面要用到
            y = torch.cat([data.y for data in test_batch]).to(predict.device)
            # 计算准确率计算一次就行了，因为两个人的结果是一样的
            loss = criterion(predict, y)
            # 计算测试集上的总损失值
            test_total_loss += loss.item()
            # 保存其中每一个mini batch计算出的结果与对应的标签。
            test_all_predicts = torch.cat((test_all_predicts, predict), dim=0)
            test_all_labels = torch.cat((test_all_labels, y), dim=0)
        # 先是打印表格，最终返回4*3的表格，并每一折叠加一次。
        metric[fold] = torch.as_tensor(np.array([list(map(float, x)) for x in test_score(test_all_predicts, test_all_labels, writer, fold, f"{fold}折中Test的loss{format(test_total_loss / len(test_dataloader), '.20f')}")]))
        # 每一折计算完之后保存一个模型文件，文件名字的格式是时间_折数——三种漏洞的f分数。
        torch.save({'model_params': model.state_dict()}, f'{config.model_data_dir}/{datetime.datetime.now()}_{fold}——{metric[fold][3]}.pth')
    # 打印平均以后的计算结果。
    utils.tqdm_write(f"K折平均值为:{torch.mean(metric, dim=0)}")
