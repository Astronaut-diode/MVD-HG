from dataset import ASTGNNDataset
from model import ASTGNNModel
from torch.nn.parallel import DistributedDataParallel
from torch.utils.data.distributed import DistributedSampler
from torch_geometric.loader import DataLoader
from sklearn.model_selection import KFold
from tqdm import tqdm
from metric import valid_score, test_score
from torch.utils.tensorboard import SummaryWriter
import numpy as np
import datetime
import sys
import config
import os
import torch
import torch.distributed as dist
import torch.multiprocessing as mp
import utils


def train():
    mp.spawn(run, nprocs=torch.cuda.device_count(), join=True)


def run(rank):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    dist.init_process_group('nccl', rank=rank, world_size=config.thread_num)
    # 核心内容都在core里面，其他的都是为了开启DDP写的。
    core(world_size=torch.cuda.device_count(), rank=rank)
    dist.destroy_process_group()


# tensorboard画图用的对象
writer = SummaryWriter(config.tensor_board_position)


# 下面才是正式开始我的内容，上面的部分是固定的DDP写法
def core(world_size, rank):
    # 获取测试集的dataset,sampler,loader
    test_dataset = ASTGNNDataset(config.data_dir_path, "test")
    test_sampler = DistributedSampler(test_dataset, num_replicas=world_size, rank=rank)
    test_loader = DataLoader(test_dataset, batch_size=config.batch_size, sampler=test_sampler)
    # 加载原始的数据集，并分割为训练集和测试集
    origin_train_dataset = ASTGNNDataset(config.data_dir_path, "train")
    # 定义K折交叉验证
    k_fold = KFold(n_splits=config.k_folds, shuffle=True)
    # 创建精度的集合，是一个3维内容，分别是折，4 * 3相当于每一折的结果都作为一个平面叠加上去。
    metric = torch.zeros((config.k_folds, 4, config.classes))
    # K折的进度条
    if rank == 0:
        k_fold_bar = tqdm(range(config.k_folds), desc="Fold ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=0)
    # K折交叉验证模型评估，对训练集进行十折划分。
    for fold, (train_ids, valid_ids) in enumerate(k_fold.split(origin_train_dataset)):
        # 获取K折以后的train和valid数据集，同时获取对应的sampler和loader
        train_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, train_ids).dataset
        train_sampler = DistributedSampler(train_dataset, num_replicas=world_size, rank=rank)
        train_loader = DataLoader(train_dataset, batch_size=config.batch_size, sampler=train_sampler)
        valid_dataset = torch.utils.data.dataset.Subset(origin_train_dataset, valid_ids).dataset
        valid_sampler = DistributedSampler(valid_dataset, num_replicas=world_size, rank=rank)
        valid_loader = DataLoader(valid_dataset, batch_size=config.batch_size, sampler=valid_sampler)
        # 加载网络，注意要先加载到GPU中，然后再开启多GPU
        model = ASTGNNModel().to(rank)
        model = DistributedDataParallel(model, device_ids=[rank])
        # 创建优化器和反向传播函数。
        optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
        criterion = torch.nn.BCEWithLogitsLoss()
        # 只有在主线程才会显示Epoch的进度条。
        if rank == 0:
            # epoch的进度条
            epoch_bar = tqdm(range(config.epoch_size), desc=f"Epoch", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=1)
        # 进行Epoch次的训练，由config配置文件中指定。
        for epoch in range(config.epoch_size):
            # 通过维持各个进程之间的相同随机数种子使不同进程能获得同样的shuffle效果。
            train_loader.sampler.set_epoch(epoch)
            # 开始训练的信号,进行训练集上的计算
            model.train()
            # 当前这一轮epoch的总损失值
            train_total_loss = 0.0
            # 截至目前已经训练过的图的张数。
            count = 0
            # 根据不同的rank创建不同的tqdm迭代器对象
            if rank == 0:
                train_batch_bar = tqdm(range(len(train_loader)), desc=f"Train", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=2)
            for index, train_batch in enumerate(train_loader):
                train_batch = train_batch.to(rank)
                # 经典的五步计算
                optimizer.zero_grad()
                # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                predict = model(train_batch)
                # 计算损失值，并进行梯度下降。
                loss = criterion(predict, train_batch.y)
                loss.backward()
                optimizer.step()
                # 计算训练集上总的损失值
                train_total_loss += loss.item()
                # 增加已经训练过图的总数
                count += len(train_batch)
                if rank == 0:
                    # 在进度条的后缀，显示当前batch的损失信息
                    train_batch_bar.set_postfix_str(f"{format(train_total_loss / count, '.4f')}")
                    # 更新train_batch的进度条。
                    train_batch_bar.update()
                    if index == len(train_loader):
                        # 关闭train的进度条
                        train_batch_bar.close()
            # 只有是主线程的时候才会打印Epoch
            if rank == 0:
                # 设置epoch进度条的后缀。
                epoch_bar.set_postfix_str(f"{format(train_total_loss, '.4f')}")
                # 更新epoch的进度条
                epoch_bar.update()
        if rank == 0:
            # Epoch全部走完了，关闭epoch的进度条
            epoch_bar.close()
        # 只在主线程上进行验证集和测试集上的操作。
        if rank == 0:
            # 关闭梯度下降,进行验证集和测试集上的操作。
            with torch.no_grad():
                # 开始验证集上的操作
                model.eval()
                # 记录验证集上计算出来的每一个结果。
                valid_all_predicts = torch.tensor([]).to(rank)
                # 记录验证集上每一个标准答案
                valid_all_labels = torch.tensor([]).to(rank)
                # 验证集上的总损失值。
                valid_total_loss = 0.0
                # 验证集上已经经过计算的图的总数，用来计算验证集的平均损失值。
                count = 0
                with tqdm(valid_loader, desc=f"Valid", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=1) as valid_batch_bar:
                    for valid_batch in valid_loader:
                        valid_batch = valid_batch.to(rank)
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(valid_batch)
                        # 计算损失值。
                        loss = criterion(predict, valid_batch.y)
                        # 计算验证集上的总损失值。
                        valid_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        valid_all_predicts = torch.cat((valid_all_predicts, predict), dim=0)
                        valid_all_labels = torch.cat((valid_all_labels, valid_batch.y), dim=0)
                        # 更新计算过的图的总数量。
                        count += len(valid_batch)
                        # 更新valid_batch的后缀信息还有进度条。
                        valid_batch_bar.set_postfix_str(f"{format(valid_total_loss / count, '.4f')}")
                        valid_batch_bar.update()
                # 先是对验证集上的结果进行画图，并打印表格，最终返回最好的阈值。
                config.reentry_threshold, config.timestamp_threshold, config.arithmetic_threshold = valid_score(valid_all_predicts, valid_all_labels, writer, f"{fold}折中Valid的loss{format(valid_total_loss / len(valid_loader), '.20f')}")
                # 进行测试集上的操作,创建两个容器，分别记录结果和原始标签。
                test_all_predicts = torch.tensor([]).to(rank)
                test_all_labels = torch.tensor([]).to(rank)
                # 测试集上的损失函数总值。
                test_total_loss = 0.0
                # 测试集上已经被处理过的图张数。
                count = 0
                with tqdm(test_loader, desc=f"Test ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=1) as test_batch_bar:
                    for test_batch in test_loader:
                        test_batch = test_batch.to(rank)
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(test_batch)
                        # 计算损失值。
                        loss = criterion(predict, test_batch.y)
                        # 计算测试集上的总损失值
                        test_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        test_all_predicts = torch.cat((test_all_predicts, predict), dim=0)
                        test_all_labels = torch.cat((test_all_labels, test_batch.y), dim=0)
                        # 更新测试集上已经经过训练的图的总张数
                        count += len(test_batch)
                        # 更新测试集进度条上的平均损失
                        test_batch_bar.set_postfix_str(f"{format(test_total_loss / count, '.4f')}")
                        test_batch_bar.update()
                # 先是打印表格，最终返回4*3的表格，并每一折叠加一次。
                metric[fold] = torch.as_tensor(np.array([list(map(float, x)) for x in test_score(test_all_predicts, test_all_labels, f"{fold}折中Test的loss{format(test_total_loss / len(test_loader), '.20f')}", rank)]))
                # 每一折计算完之后保存一个模型文件，文件名字的格式是时间_折数——三种漏洞的f分数。
                torch.save({'model_params': model.state_dict()}, f'{config.model_data_dir}/{datetime.datetime.now()}_{fold}——{metric[fold][3]}.pth')
        if rank == 0:
            # 更新K折的进度条
            k_fold_bar.update()
    # 只有在主线程才会打印
    if rank == 0:
        # 关闭K折的进度条。
        k_fold_bar.close()
        # 打印平均以后的计算结果。
        utils.tqdm_write(f"K折平均值为:{torch.mean(metric, dim=0)}")
