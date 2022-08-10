# coding=UTF-8
from dataset import ASTGNNDataset
from model import ASTGNNModel
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

# 主GPU，内容都先加载到这上面来。
main_device = torch.device(config.main_device)
writer = SummaryWriter(config.tensor_board_position)
# 保证DataListLoader多线程加载数据的时候不会出现错误。
torch.multiprocessing.set_sharing_strategy('file_system')


def train():
    # 分割为训练集和测试集，下面再对训练集进行K折交叉验证的操作。
    origin_train_dataset = ASTGNNDataset(config.data_dir_path, "train")
    test_dataset = ASTGNNDataset(config.data_dir_path, "test")
    # 使用Loader加载数据集
    test_dataloader = DataListLoader(dataset=test_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False, num_workers=config.num_workers)
    # 定义K折交叉验证
    k_fold = KFold(n_splits=config.k_folds, shuffle=True)
    # 创建精度的集合，是一个3维内容，分别是折，4 * 3相当于每一折的结果都作为一个平面叠加上去。
    metric = torch.zeros((config.k_folds, 4, config.classes))
    # K折的进度条
    with tqdm(range(config.k_folds), desc="Fold ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout) as k_fold_bar:
        # K折交叉验证模型评估，对训练集进行十折划分。
        for fold, (train_ids, valid_ids) in enumerate(k_fold.split(origin_train_dataset)):
            # 获取K折以后的train和valid数据集
            train_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, train_ids).dataset
            valid_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, valid_ids).dataset
            # 将训练集和验证集加载到loader中。

            train_dataloader = DataListLoader(dataset=train_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False, num_workers=config.num_workers)
            valid_dataloader = DataListLoader(dataset=valid_dataset, batch_size=config.batch_size, shuffle=True, drop_last=False, num_workers=config.num_workers)
            # 加载网络，这里是为了避免使用同一个网络，对于不同的K折交叉验证会有影响。
            model = ASTGNNModel()
            # 使用多GPU，注意，使用的卡是直接配置好的gpu_id以后转换的从零开始的数组。
            model = DataParallel(model, device_ids=config.device_ids)
            # 将模型转化为在主设备上运行的类型。
            model = model.to(main_device)
            # 创建优化器和反向传播函数。
            optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
            criterion = torch.nn.BCEWithLogitsLoss()
            # epoch的进度条
            with tqdm(range(config.epoch_size), desc="Epoch", leave=False, ncols=config.tqdm_ncols, file=sys.stdout) as epoch_bar:
                # 进行Epoch次的训练，由config配置文件中指定。
                for epoch in range(config.epoch_size):
                    # 开始训练的信号,进行训练集上的计算
                    model.train()
                    # 当前这一轮epoch的总损失值
                    train_total_loss = 0.0
                    # 截至目前已经训练过的图的张数。
                    count = 0
                    # train_batch的进度条。
                    with tqdm(train_dataloader, desc="Train", leave=False, ncols=config.tqdm_ncols, file=sys.stdout) as train_batch_bar:
                        for train_batch in train_dataloader:
                            # 经典的五步计算
                            optimizer.zero_grad()
                            # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                            predict = model(train_batch)
                            # 单独拿出y因为后面要用到，同时将他转化为主设备上的数据。
                            y = torch.cat([data.y for data in train_batch]).to(predict.device)
                            # 计算损失值，并进行梯度下降。
                            loss = criterion(predict, y)
                            loss.backward()
                            optimizer.step()
                            # 计算训练集上总的损失值
                            train_total_loss += loss.item()
                            # 增加已经训练过图的总数
                            count += len(train_batch)
                            # 在进度条的后缀，显示当前batch的损失信息
                            train_batch_bar.set_postfix_str(f"{format(train_total_loss / count, '.4f')}")
                            # 更新train_batch的进度条。
                            train_batch_bar.update()
                    # 设置epoch进度条的后缀。
                    epoch_bar.set_postfix_str(f"{format(train_total_loss, '.4f')}")
                    # 更新epoch进度条
                    epoch_bar.update()
            # 关闭梯度下降,进行验证集和测试集上的操作。
            with torch.no_grad():
                # 开始验证集上的操作
                model.eval()
                # 记录验证集上计算出来的每一个结果。
                valid_all_predicts = torch.tensor([]).to(main_device)
                # 记录验证集上每一个标准答案
                valid_all_labels = torch.tensor([]).to(main_device)
                # 验证集上的总损失值。
                valid_total_loss = 0.0
                # 验证集上已经经过计算的图的总数，用来计算验证集的平均损失值。
                count = 0
                with tqdm(valid_dataloader, desc=f"Valid", leave=False, ncols=config.tqdm_ncols, file=sys.stdout) as valid_batch_bar:
                    for valid_batch in valid_dataloader:
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(valid_batch)
                        # 单独拿出y因为后面要用到，同时转化为和predict一样的设备上。
                        y = torch.cat([data.y for data in valid_batch]).to(predict.device)
                        # 计算损失值。
                        loss = criterion(predict, y)
                        # 计算验证集上的总损失值。
                        valid_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        valid_all_predicts = torch.cat((valid_all_predicts, predict), dim=0)
                        valid_all_labels = torch.cat((valid_all_labels, y), dim=0)
                        # 更新计算过的图的总数量。
                        count += len(valid_batch)
                        # 更新valid_batch的后缀信息还有进度条。
                        valid_batch_bar.set_postfix_str(f"{format(valid_total_loss / count, '.4f')}")
                        valid_batch_bar.update()
                # 先是对验证集上的结果进行画图，并打印表格，最终返回最好的阈值。
                config.reentry_threshold, config.timestamp_threshold, config.arithmetic_threshold = valid_score(valid_all_predicts, valid_all_labels, writer, f"{fold}折中Valid的loss{format(valid_total_loss / len(valid_dataloader), '.20f')}")
                # 进行测试集上的操作,创建两个容器，分别记录结果和原始标签。
                test_all_predicts = torch.tensor([]).to(main_device)
                test_all_labels = torch.tensor([]).to(main_device)
                # 测试集上的损失函数总值。
                test_total_loss = 0.0
                # 测试集上已经被处理过的图张数。
                count = 0
                with tqdm(test_dataloader, desc=f"Test ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout) as test_batch_bar:
                    for test_batch in test_dataloader:
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(test_batch)
                        # 单独拿出y因为后面要用到，并转化为和predict一个设备上。
                        y = torch.cat([data.y for data in test_batch]).to(predict.device)
                        # 计算损失值。
                        loss = criterion(predict, y)
                        # 计算测试集上的总损失值
                        test_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        test_all_predicts = torch.cat((test_all_predicts, predict), dim=0)
                        test_all_labels = torch.cat((test_all_labels, y), dim=0)
                        # 更新测试集上已经经过训练的图的总张数
                        count += len(test_batch)
                        # 更新测试集进度条上的平均损失
                        test_batch_bar.set_postfix_str(f"{format(test_total_loss / count, '.4f')}")
                        test_batch_bar.update()
                # 先是打印表格，最终返回4*3的表格，并每一折叠加一次。
                metric[fold] = torch.as_tensor(np.array([list(map(float, x)) for x in test_score(test_all_predicts, test_all_labels, f"{fold}折中Test的loss{format(test_total_loss / len(test_dataloader), '.20f')}")]))
                # 每一折计算完之后保存一个模型文件，文件名字的格式是时间_折数——三种漏洞的f分数。
                torch.save({'model_params': model.state_dict()}, f'{config.model_data_dir}/{datetime.datetime.now()}_{fold}——{metric[fold][3]}.pth')
            # 更新K折的进度条
            k_fold_bar.update()
    # 打印平均以后的计算结果。
    utils.tqdm_write(f"K折平均值为:{torch.mean(metric, dim=0)}")
