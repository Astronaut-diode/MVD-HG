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
    # 如果processed文件夹存在，而且内容不是空，那就说明数据集已经生成好了，直接进行训练即可。
    if os.path.exists(config.data_process_dir_path) and os.listdir(config.data_process_dir_path):
        attack_type_list = ["reentry", "timestamp", "arithmetic"]
        # 遍历每一种漏洞类型进行训练。
        for attack_type in attack_type_list:
            attack_index = config.attack_list.index(attack_type)
            args = (attack_index, attack_type)
            mp.spawn(run, args=args, nprocs=torch.cuda.device_count(), join=True)
    # 否则随便生成一个数据集就结束。
    else:
        ASTGNNDataset(config.data_dir_path, "test", "reentry", 0)


def run(rank, attack_index: int, attack_type: str):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    dist.init_process_group('nccl', rank=rank, world_size=config.thread_num)
    # 核心内容都在core里面，其他的都是为了开启DDP写的。
    core(world_size=torch.cuda.device_count(), rank=rank, attack_index=attack_index, attack_type=attack_type)
    dist.destroy_process_group()


# tensorboard画图用的对象
writer = SummaryWriter(config.tensor_board_position)


# 下面才是正式开始我的内容，上面的部分是固定的DDP写法
def core(world_size, rank, attack_index, attack_type):
    # 获取原始的训练集，这样子每一种漏洞检测只需要简单的加载一次，后面直接通过update方法，改变使用的dataset即可。
    dataset = ASTGNNDataset(config.data_dir_path, attack_type)
    # 定义K折交叉验证
    k_fold = KFold(n_splits=config.k_folds, shuffle=True)
    # 创建精度的集合，是一个3维内容，分别是折，4 * 1相当于每一折的结果都作为一个平面叠加上去。
    metric = torch.zeros((config.k_folds, 4, 1))
    # K折的进度条
    if rank == 0:
        k_fold_bar = tqdm(range(config.k_folds), desc="Fold ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=0)
    # 改变为原始的训练集
    dataset.update_dataset(mode="origin_train")
    # K折交叉验证模型评估，对训练集进行十折划分。
    for fold, (train_ids, valid_ids) in enumerate(k_fold.split(dataset)):
        # 传入train_ids，转换为训练集模式
        dataset.update_dataset(mode="train", train_indices=train_ids)
        train_sampler = DistributedSampler(dataset=dataset, num_replicas=world_size, rank=rank)
        train_loader = DataLoader(dataset=dataset, batch_size=config.batch_size, sampler=train_sampler)
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
                loss = criterion(predict, train_batch.y[:, attack_index].view(predict.shape))
                loss.backward()
                optimizer.step()
                # 计算训练集上总的损失值
                train_total_loss += loss.item()
                # 增加已经训练过图的总数
                count += len(train_batch)
                if rank == 0:
                    # 设置epoch进度条的后缀。
                    epoch_bar.set_postfix_str(f"{format(train_total_loss, '.4f')}")
                    # 在进度条的后缀，显示当前batch的损失信息
                    train_batch_bar.set_postfix_str(f"{format(train_total_loss / count, '.4f')}_当前在用{int(torch.cuda.memory_allocated(device=0) / 1024 / 1024)}_已分配{int(torch.cuda.max_memory_allocated(device=0) / 1024 / 1024)}_保留部分{int(torch.cuda.memory_reserved(device=0) / 1024 / 1024)}")
                    # 更新train_batch的进度条。
                    train_batch_bar.update()
            # 只有是主线程的时候才会打印Epoch
            if rank == 0:
                # 关闭train的进度条
                train_batch_bar.close()
                # 更新epoch的进度条
                epoch_bar.update()
        # 同步一下线程
        dist.barrier()
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
                # 传入valid_ids，转换为验证集模式。
                dataset.update_dataset(mode="train", valid_indices=valid_ids)
                valid_loader = DataLoader(dataset=dataset, batch_size=config.batch_size)
                with tqdm(valid_loader, desc=f"Valid", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=1) as valid_batch_bar:
                    for valid_batch in valid_loader:
                        valid_batch = valid_batch.to(rank)
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(valid_batch)
                        # 计算损失值。
                        loss = criterion(predict, valid_batch.y[:, attack_index].view(predict.shape))
                        # 计算验证集上的总损失值。
                        valid_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        valid_all_predicts = torch.cat((valid_all_predicts, predict), dim=0)
                        valid_all_labels = torch.cat((valid_all_labels, valid_batch.y[:, attack_index]), dim=0)
                        # 更新计算过的图的总数量。
                        count += len(valid_batch)
                        # 更新valid_batch的后缀信息还有进度条。
                        valid_batch_bar.set_postfix_str(f"{format(valid_total_loss / count, '.4f')}_当前在用{int(torch.cuda.memory_allocated() / 1024 / 1024)}_已分配{int(torch.cuda.max_memory_allocated() / 1024 / 1024)}_保留部分{int(torch.cuda.memory_reserved() / 1024 / 1024)}")
                        valid_batch_bar.update()
                # 先是对验证集上的结果进行画图，并打印表格，最终返回最好的阈值。
                config.threshold = valid_score(valid_all_predicts, valid_all_labels, writer, f"{attack_type}_{fold}折中Valid的loss{format(valid_total_loss / len(valid_loader), '.10f')}", attack_index, attack_type)
                # 进行测试集上的操作,创建两个容器，分别记录结果和原始标签。
                test_all_predicts = torch.tensor([]).to(rank)
                test_all_labels = torch.tensor([]).to(rank)
                # 测试集上的损失函数总值。
                test_total_loss = 0.0
                # 测试集上已经被处理过的图张数。
                count = 0
                # 改变为测试集
                dataset.update_dataset(mode="test")
                test_loader = DataLoader(dataset=dataset, batch_size=config.batch_size)
                with tqdm(test_loader, desc=f"Test ", leave=False, ncols=config.tqdm_ncols, file=sys.stdout, position=1) as test_batch_bar:
                    for test_batch in test_loader:
                        test_batch = test_batch.to(rank)
                        # 传入batch，因为是多GPU所以会将batch一个个拆分，送入到模型中进行训练。
                        predict = model(test_batch)
                        # 计算损失值。
                        loss = criterion(predict, test_batch.y[:, attack_index].view(predict.shape))
                        # 计算测试集上的总损失值
                        test_total_loss += loss.item()
                        # 保存其中每一个mini batch计算出的结果与对应的标签。
                        test_all_predicts = torch.cat((test_all_predicts, predict), dim=0)
                        test_all_labels = torch.cat((test_all_labels, test_batch.y[:, attack_index]), dim=0)
                        # 更新测试集上已经经过训练的图的总张数
                        count += len(test_batch)
                        # 更新测试集进度条上的平均损失
                        test_batch_bar.set_postfix_str(f"{format(test_total_loss / count, '.4f')}_当前在用{int(torch.cuda.memory_allocated() / 1024 / 1024)}_已分配{int(torch.cuda.max_memory_allocated() / 1024 / 1024)}_保留部分{int(torch.cuda.memory_reserved() / 1024 / 1024)}")
                        test_batch_bar.update()
                # 先是打印表格，最终返回4*1的表格，并每一折叠加一次。
                metric[fold] = torch.as_tensor(np.array([list(map(float, x)) for x in test_score(test_all_predicts, test_all_labels, f"{attack_type}_{fold}折中Test的loss{format(test_total_loss / len(test_loader), '.10f')}", rank, attack_index, attack_type)]))
                # 每一折计算完之后保存一个模型文件，文件名字的格式是时间_折数——三种漏洞的f分数。
                torch.save({'model_params': model.state_dict()}, f'{config.model_data_dir}/{attack_type}_{datetime.datetime.now()}_{fold}——{metric[fold][3]}.pth')
        if rank == 0:
            # 更新K折的进度条
            k_fold_bar.update()
        # 后续进来的时候也得是origin_train_data,否则无法切分数据集，所以需要改回来。
        dataset.update_dataset(mode="origin_train")
        # 同步双线程的进度
        dist.barrier()
    # 只有在主线程才会打印
    if rank == 0:
        # 关闭K折的进度条。
        k_fold_bar.close()
        # 打印平均以后的计算结果。
        utils.tqdm_write(f"K折平均值为:{torch.mean(metric, dim=0)}")
