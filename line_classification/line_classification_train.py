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
import math
import torch
import utils


def line_classification_train():
    while True:
        # 获取完整的行级数据集，并直接分割为两部分
        total_dataset = line_classification_dataset(config.data_dir_path)
        split = int(len(total_dataset) * 0.7)
        train_dataset = total_dataset[0:split]
        test_dataset = total_dataset[split:]
        buggy1 = 0
        clear1 = 0
        tmp = DataLoader(dataset=train_dataset, batch_size=1)
        for index, t in enumerate(tmp):
            for i in t.contract_buggy_line[0]:
                if i == 1:
                    buggy1 += 1
                else:
                    clear1 += 1
        buggy2 = 0
        clear2 = 0
        tmp = DataLoader(dataset=test_dataset, batch_size=1)
        for index, t in enumerate(tmp):
            for i in t.contract_buggy_line[0]:
                if i == 1:
                    buggy2 += 1
                else:
                    clear2 += 1
        if buggy1 != 0 and clear1 != 0 and buggy2 != 0 and clear2 != 0:
            utils.tip(f'{buggy1} {buggy2} {clear1} {clear2}')
            break
    # 获取行级别漏洞检测的模型。
    model = line_classification_model().to(config.device)
    # 这里就直接定死batch_size设置为1，反正数据集也很小，不需要特殊处理。
    train_loader = DataLoader(dataset=train_dataset, batch_size=1)
    # 创建优化器和反向传播函数。
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    # 学习率优化器
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, config.learning_change_epoch, gamma=config.learning_change_gamma, last_epoch=-1)
    criterion = torch.nn.BCELoss()
    train_start_time = datetime.datetime.now()
    line_train_all_predicts = torch.tensor([]).to(config.device)
    line_train_all_labels = torch.tensor([]).to(config.device)
    train_total_loss_list = []
    for epoch in range(config.epoch_size):
        # 更新学习率
        scheduler.step()
        # 开始训练的信号,进行训练集上的计算
        model.train()
        # 当前这一轮epoch的总损失值
        train_total_loss = 0.0
        # 截至目前已经训练过的图的张数。
        count = 0
        predict_batch = torch.tensor([]).to(config.device)
        stand_batch = torch.tensor([]).to(config.device)
        for index, train in enumerate(train_loader):
            train = train.to(config.device)
            optimizer.zero_grad()
            predict, stand = model(train)
            line_train_all_predicts = torch.cat((line_train_all_predicts, predict), dim=0)
            line_train_all_labels = torch.cat((line_train_all_labels, stand.view(-1, 1)), dim=0)
            predict_batch = torch.cat((predict_batch, predict), dim=0)
            stand_batch = torch.cat((stand_batch, stand.view(-1, 1)), dim=0)
            if (index + 1) % config.batch_size == 0 or index + 1 == len(train_loader):
                loss = criterion(predict_batch, stand_batch.view(predict_batch.shape).to(torch.float32))
                predict_batch = torch.tensor([]).to(config.device)
                stand_batch = torch.tensor([]).to(config.device)
                loss.backward()
                optimizer.step()
                # 计算训练时刻行级别的准确率以及损失值。
                train_total_loss += loss.item()
            # loss = criterion(predict, stand.view(predict.shape).to(torch.float32))
            # loss.backward()
            # optimizer.step()
            # # 计算训练时刻行级别的准确率以及损失值。
            # train_total_loss += loss.item()
            count += len(train)
        utils.tip(f"epoch{epoch + 1}.结束，一共训练了{count}张图, 总损失值为: {train_total_loss}，学习率为:{optimizer.state_dict()['param_groups'][0]['lr']}")
        # 判断是不是梯度消失了，如果确定，那么就结束本次重新开始
        train_total_loss_list.append(train_total_loss)
        if len(train_total_loss_list) > 2:
            # 平均每张图的损失达到了0.3或者恒定大于50，并且变化率极小的时候，直接重开。
            if (train_total_loss_list[-3] > config.exception_for_graph_per * count and train_total_loss_list[-2] > config.exception_for_graph_per * count and train_total_loss_list[-1] > config.exception_for_graph_per * count) or (train_total_loss_list[-3] > config.exception_for_graph_abs and train_total_loss_list[-2] > config.exception_for_graph_abs and train_total_loss_list[-1] > config.exception_for_graph_abs):
                a = train_total_loss_list[-3]
                b = train_total_loss_list[-2]
                diff1 = abs(a - b)
                c = train_total_loss_list[-1]
                diff2 = abs(b - c)
                diff_threshold1 = diff1 / b
                diff_threshold2 = diff2 / c
                if diff_threshold1 < config.disappear_threshold and diff_threshold2 < config.disappear_threshold:
                    utils.error("本次训练梯度消失，准备开始重新当前次实验。")
                    return [math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan]
    # 根据所有epoch的训练结果，求出最优的异常阈值，待会给验证集使用。
    # 暂时转换为cpu上的不然gpu会oom
    line_train_all_predicts = line_train_all_predicts.to("cpu")
    line_train_all_labels = line_train_all_labels.to("cpu")
    config.threshold = get_best_metric(line_train_all_predicts, line_train_all_labels, "所有epoch的结果放在一起计算最优的阈值")["probability"]
    train_end_time = datetime.datetime.now()
    eval_start_time = datetime.datetime.now()
    # 验证部分
    model.eval()
    test_loader = DataLoader(dataset=test_dataset, batch_size=1)
    # 行级别的预测标签以及正确标签
    line_test_all_predicts = torch.tensor([]).to(config.device)
    line_test_all_labels = torch.tensor([]).to(config.device)
    for index, test in enumerate(test_loader):
        test = test.to(config.device)
        predict, stand = model(test)
        # for i in range(predict.shape[0]):
            # if (predict[i] > 0.5).add(0) != stand[i]:
                # utils.error(f"判断错误的行是{test.owner_file[0][0]} {i + 1} predict{predict[i]} stand{stand[i]}")
        # 记录所有的标签和预测结果
        line_test_all_predicts = torch.cat((line_test_all_predicts, predict), dim=0)
        line_test_all_labels = torch.cat((line_test_all_labels, stand.view(-1, 1)), dim=0)
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
    # 使用最优的阈值求出对应的结果。
    optimal_list = test_score(line_test_all_predicts, line_test_all_labels, f"{config.attack_type_name}类型行级结果", config.attack_type_name)
    return [optimal_list[0], optimal_list[1], optimal_list[2], optimal_list[3],
            train_end_time - train_start_time, eval_end_time - eval_start_time, len(total_dataset), total_edge_number, total_node_number, len(train_dataset), len(test_dataset)]


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
    predict_matrix = (predict >= torch.as_tensor(data=[config.threshold]).to(config.device)).add(0)
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


# 找出最好的阈值，用来计算出的结果。
# predict：预测结果，是概率的一维数组，长度和标签一样长。
# label:标签
def get_best_metric(predict, label, msg):
    # 求出其中的最佳值，然后返回。
    best_res = {"probability": 0, "accuracy": 0, "precision": 0, "recall": 0, "f_score": 0}
    # 取出所有的不同的概率，然后将概率转换为0和1的predict_matrix矩阵,注意，如果种类太多，会导致GPU都存不下，所以需要少取一些，这里取步长为100好了。
    unique_probability = torch.unique(predict).reshape(-1, 1)
    # 通过步长重新选取，免得取得太多了，内存爆炸。
    unique_probability = unique_probability[::math.ceil(len(unique_probability) / config.threshold_max_classes)]
    predict_matrix = (predict.view(1, -1) >= unique_probability.view(-1, 1)).add(0)
    label = label.T
    # 根据标签矩阵和预测矩阵，求出四个基础标签。
    tp = torch.sum(torch.logical_and(label, predict_matrix), dim=1).reshape(-1, 1)
    fp = torch.sum(torch.logical_and(torch.sub(1, label), predict_matrix), dim=1).reshape(-1, 1)
    tn = torch.sum(torch.logical_and(torch.sub(1, label), torch.sub(1, predict_matrix)), dim=1).reshape(-1, 1)
    fn = torch.sum(torch.logical_and(label, torch.sub(1, predict_matrix)), dim=1).reshape(-1, 1)
    # 由四个基础标签求出对应的四种参数。
    accuracy = tp.add(tn).div(tp.add(fp).add(tn).add(fn))
    precision = tp.div(tp.add(fp))
    recall = tp.div(tp.add(fn))
    f_score = tp.mul(1 + config.beta ** 2).div(tp.mul(1 + config.beta ** 2).add(fn.mul(config.beta ** 2).add(fp).add(config.epsilon)))
    # 根据p和r的和，决定谁是效果最好的，直接返回这组结果。
    # best_sample_index = precision.add(recall).argmax(dim=0)
    # 改成求出最大的f分数
    best_sample_index = f_score.argmax(dim=0)
    # 取出每一种度量标准中的最大得分。
    best_res["probability"] = unique_probability[best_sample_index, 0]
    best_res["accuracy"] = accuracy[best_sample_index, 0]
    best_res["precision"] = precision[best_sample_index, 0]
    best_res["recall"] = recall[best_sample_index, 0]
    best_res["f_score"] = f_score[best_sample_index, 0]
    table = PrettyTable(['', f"最优概率为{best_res['probability']}"])
    table._table_width = config.table_width
    table.title = msg
    table.add_row(["Accuracy", best_res['accuracy']])
    table.add_row(["Precision", best_res['precision']])
    table.add_row(["Recall", best_res['recall']])
    table.add_row(["F-score", best_res['f_score']])
    utils.tqdm_write(table)
    return best_res
