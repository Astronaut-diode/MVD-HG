from contract_classification.contract_classification_dataset import contract_classification_dataset
from contract_classification.contract_classification_model import contract_classification_model
from prettytable import PrettyTable
from torch_geometric.loader import DataLoader
from tqdm import tqdm
import numpy as np
import datetime
import sys
import config
import os
import torch
import utils


def contract_classification_train():
    while True:
        # 获取完整的合约数据集，并直接分割为测试集和验证集两部分。
        total_dataset = contract_classification_dataset(config.data_dir_path)
        split = int(len(total_dataset) * 0.7)
        train_dataset = total_dataset[0:split]
        test_dataset = total_dataset[split:]
        buggy1 = 0
        clear1 = 0
        tmp = DataLoader(dataset=train_dataset, batch_size=1)
        for index, t in enumerate(tmp):
            for i in t.contract_buggy_record:
                if t.contract_buggy_record[i].item() == 1:
                    buggy1 += 1
                else:
                    clear1 += 1
        buggy2 = 0
        clear2 = 0
        tmp = DataLoader(dataset=test_dataset, batch_size=1)
        for index, t in enumerate(tmp):
            for i in t.contract_buggy_record:
                if t.contract_buggy_record[i].item() == 1:
                    buggy2 += 1
                else:
                    clear2 += 1
        if buggy1 != 0 and clear1 != 0 and buggy2 != 0 and clear2 != 0:
            utils.tip(f"{buggy1} {buggy2} {clear1} {clear2}")
            break
    # 获取模型。
    model = contract_classification_model()
    train_loader = DataLoader(dataset=train_dataset, batch_size=1)
    # 创建优化器和反向传播函数
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = torch.nn.BCELoss()
    train_start_time = datetime.datetime.now()
    for epoch in range(config.epoch_size):
        # 开始训练
        model.train()
        # 当前这一轮epoch的总损失值
        total_loss_of_now_epoch = 0.0
        # 截至到目前已经训练的图数量(也就是合约的数量)
        count = 0
        # 计算正确的contract的数量
        correct = 0
        # 所有经过训练的contract的数量。
        total = 0
        for index, train in enumerate(train_loader):
            optimizer.zero_grad()
            # 这里的predict是代表每一个合约是否含有漏洞，注意，返回的顺序需要和built_vector_dataset中的内容一致。
            predict, stand = model(train)
            loss = criterion(predict, stand.view(predict.shape).to(torch.float32))
            loss.backward()
            optimizer.step()
            total_loss_of_now_epoch += loss.item()
            predict[predict > 0.5] = 1
            predict[predict <= 0.5] = 0
            correct += (predict.T == stand).sum()
            total += predict.size(0)
            count += len(train)
        utils.tip(f"{epoch + 1}.结束，一共训练了{count}张图, 准确率为: {(correct / total).item()}, %总损失值为: {total_loss_of_now_epoch}")
    train_end_time = datetime.datetime.now()
    eval_start_time = datetime.datetime.now()
    # 开始验证集部分。
    model.eval()
    test_loader = DataLoader(dataset=test_dataset, batch_size=1)
    test_all_predict_labels = torch.tensor([])
    test_all_stand_labels = torch.tensor([])
    for index, test in enumerate(test_loader):
        predict, stand = model(test)
        predict[predict > 0.5] = 1
        predict[predict <= 0.5] = 0
        test_all_predict_labels = torch.cat((test_all_predict_labels, predict), dim=0)
        test_all_stand_labels = torch.cat((test_all_stand_labels, stand.view(-1, 1)), dim=0)
    eval_end_time = datetime.datetime.now()
    loader = DataLoader(dataset=total_dataset, batch_size=1)
    total_edge_number = 0
    total_node_number = 0
    for data in loader:
        total_edge_number += data.edge_index.shape[1]
        total_node_number += data.x.shape[0]
    utils.tip(f"总共的训练集共有{len(total_dataset)}张图，边有{total_edge_number}条，节点有{total_node_number}")
    utils.tip(f"训练{config.epoch_size}轮一共耗时{train_end_time - train_start_time}")
    utils.tip(f"训练图共有{split + 1}张")
    utils.tip(f"验证一共耗时{eval_end_time - eval_start_time}")
    utils.tip(f"验证图共有{len(total_dataset) - (split + 1)}张")
    optimal_list = test_score(test_all_predict_labels, test_all_stand_labels, f"{config.attack_type_name}类型合约级结果", config.attack_type_name)
    return [optimal_list[0], optimal_list[1], optimal_list[2], optimal_list[3], train_end_time - train_start_time, eval_end_time - eval_start_time, len(total_dataset), total_edge_number, total_node_number, len(train_dataset), len(test_dataset)]


# 测试集上的度量方法，阈值已经由config中给出。
# predict:预测结果
# label:原始标签
# writer:tensor board画图用的
# fold:外面的交叉验证到哪一步了。
# model:代表不同的模式
def test_score(predict, label, msg, attack_type):
    predict = predict.data
    label = label.data.view(-1, 1)
    # 结果矩阵，里面存放的是四种漏洞类型的四种基础衡量标准。
    optimal_list = [[""],
                    [""],
                    [""],
                    [""]]
    # 先将预测值转化为标签内容,记住要将内容转化到主GPU上。
    predict_matrix = (predict >= 0.5).add(0)
    # 这里的结果是一个一行3列的数组，分别代表不同漏洞的TP,FP,TN,FN。
    tp = torch.sum(torch.logical_and(label, predict_matrix), dim=0).reshape(-1, 1)
    fp = torch.sum(torch.logical_and(torch.sub(1, label), predict_matrix), dim=0).reshape(-1, 1)
    tn = torch.sum(torch.logical_and(torch.sub(1, label), torch.sub(1, predict_matrix)), dim=0).reshape(-1, 1)
    fn = torch.sum(torch.logical_and(label, torch.sub(1, predict_matrix)), dim=0).reshape(-1, 1)
    # 由四个基础标签求出对应的四种参数。
    optimal_list[0] = tp.add(tn).div(tp.add(fp).add(tn).add(fn))
    optimal_list[1] = tp.div(tp.add(fp))
    optimal_list[2] = tp.div(tp.add(fn))
    optimal_list[3] = tp.mul(1 + config.beta ** 2).div(tp.mul(1 + config.beta ** 2).add(fn.mul(config.beta ** 2).add(fp).add(config.epsilon)))
    # 打印一下看一下三种漏洞类型的精度之类的，而且这里可以放大版面。
    table = PrettyTable(['', attack_type])
    table._table_width = config.table_width
    table.title = msg
    table.add_row(["Accuracy", f"{format(optimal_list[0][0].item(), '.30f')}"])
    table.add_row(["Precision", f"{format(optimal_list[1][0].item(), '.30f')}"])
    table.add_row(["Recall", f"{format(optimal_list[2][0].item(), '.30f')}"])
    table.add_row(["F-score", f"{format(optimal_list[3][0].item(), '.30f')}"])
    utils.tqdm_write(table)
    # 返回每一个测试集上的计算结果，然后最终用来求平均。
    return optimal_list
