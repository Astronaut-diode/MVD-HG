from line_classification.line_classification_dataset import line_classification_dataset
from line_classification.line_classification_model import line_classification_model
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


def line_classification_train():
    # 获取完整的行级数据集，并直接分割为两部分
    total_dataset = line_classification_dataset(config.data_dir_path)
    train_dataset = total_dataset[0:42]
    test_dataset = total_dataset[42:]
    # 获取行级别漏洞检测的模型。
    model = line_classification_model()
    # 这里就直接定死batch_size设置为1，反正数据集也很小，不需要特殊处理。
    train_loader = DataLoader(dataset=train_dataset, batch_size=1)
    # 创建优化器和反向传播函数。
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    criterion = torch.nn.BCELoss()
    for epoch in range(config.epoch_size):
        # 开始训练的信号,进行训练集上的计算
        model.train()
        # 当前这一轮epoch的总损失值
        train_total_loss = 0.0
        # 截至目前已经训练过的图的张数。
        count = 0
        # 节点级别计算正确的数量
        correct = 0
        # 节点级别已经计算的节点总数量
        total = 0
        for index, train in enumerate(train_loader):
            optimizer.zero_grad()
            predict = model(train)
            loss = criterion(predict, train.line_classification_label.view(predict.shape).to(torch.float32))
            loss.backward()
            optimizer.step()
            # 计算训练时刻节点级别的准确率以及损失值。
            train_total_loss += loss.item()
            predict[predict > 0.5] = 1
            predict[predict <= 0.5] = 0
            correct += (predict.T == train.line_classification_label).sum()
            count += len(train)
            total += predict.size(0)
        print(f"{epoch + 1}.结束，一共训练了{count}张图")
        print("准确率为:", (correct / total).item(), "%总损失值为:", train_total_loss)
    # 验证部分
    model.eval()
    test_loader = DataLoader(dataset=test_dataset, batch_size=1)
    # 节点级别的预测标签以及正确标签
    node_test_all_predicts = torch.tensor([])
    node_test_all_labels = torch.tensor([])
    # 行级别的预测标签以及正确标签
    line_test_all_predicts = torch.tensor([])
    line_test_all_labels = torch.tensor([])
    for index, test in enumerate(test_loader):
        predict = model(test)
        predict[predict > 0.5] = 1
        predict[predict <= 0.5] = 0
        # 记录节点级别的总标签，方便一整个验证集计算完毕以后直接计算完整的四种度量标准。
        node_test_all_predicts = torch.cat((node_test_all_predicts, predict), dim=0)
        node_test_all_labels = torch.cat((node_test_all_labels, test.line_classification_label), dim=0)
        # 记录当前文件为所有行打的标签，以此来计算四种度量标准
        line_predict = [0] * (len(test.contract_buggy_line[0]))
        for jndex, pre in enumerate(predict.T[0]):
            if test.line_classification_label[jndex] == 1:
                line_predict[test[0].owner_line[jndex] - 1] = 1
        # 记录行级别的总标签，方便一整个验证集计算完毕以后直接计算完整的四种度量标准。
        line_test_all_predicts = torch.cat((line_test_all_predicts, torch.tensor(line_predict).view(-1, 1)), dim=0)
        line_test_all_labels = torch.cat((line_test_all_labels, torch.tensor(test.contract_buggy_line[0])), dim=0)
        # 为每一个单独的文件计算对应的行级别的四种度量标准。
        test_score(torch.tensor(line_predict).view(-1, 1), torch.tensor(test.contract_buggy_line[0]), f"第{index}张图{test.owner_file[0][0][test.owner_file[0][0].rfind('/') + 1:]}行级的结果", config.attack_type_name)
    test_score(line_test_all_predicts, line_test_all_labels, f"{config.attack_type_name}类型行级别结果", config.attack_type_name)
    test_score(node_test_all_predicts, node_test_all_labels, f"{config.attack_type_name}类型节点级结果", config.attack_type_name)


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
