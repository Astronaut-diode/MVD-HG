import config
import utils
import torch
import math
from prettytable import PrettyTable


# 计算出三种漏洞的各种最优的属性
# predict:预测结果
# label:原始标签
# writer:tensor board画图用的
# fold:外面的交叉验证到哪一步了。
# epoch:交叉验证中已经到了哪一个世代了。
def score(predict, label, writer, fold, epoch, msg, draw):
    predict = predict.data
    label = label.data
    # 结果矩阵，里面存放的是四种漏洞类型的四种基础衡量标准。
    optimal_list = [["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""]]
    # 取出第i中类型的预测结果和原始标签，输入到阈值调优中进行调优
    for attack_index in range(config.classes):
        res = threshold_optimize(predict[:, attack_index], label[:, attack_index], writer, fold, epoch, attack_index, draw)
        # 三种漏洞的四种度量标准，一行是同一种度量，但是是不同的错误类型。
        optimal_list[0][attack_index] = f"{format(res['accuracy'].item(), '.30f')}"
        optimal_list[1][attack_index] = f"{format(res['precision'].item(), '.30f')}"
        optimal_list[2][attack_index] = f"{format(res['recall'].item(), '.30f')}"
        optimal_list[3][attack_index] = f"{format(res['f_score'].item(), '.30f')}"
    # 打印一下看一下三种漏洞类型的精度之类的，而且这里可以放大版面。
    table = PrettyTable(['', 'Reentry', 'TimeStamp', 'Arithmetic'], )
    table._table_width = config.table_width
    table.title = msg
    table.add_row(["Accuracy", optimal_list[0][0], optimal_list[0][1], optimal_list[0][2]])
    table.add_row(["Precision", optimal_list[1][0], optimal_list[1][1], optimal_list[1][2]])
    table.add_row(["Recall", optimal_list[2][0], optimal_list[2][1], optimal_list[2][2]])
    table.add_row(["F-score", optimal_list[3][0], optimal_list[3][1], optimal_list[3][2]])
    utils.tqdm_write(table)


# 将多标签分类为多种单标签，以进行阈值调优。
# predict：预测结果，是概率的一维数组，长度和标签一样长。
# writer画tensor board的时候用的。
# fold:到了第几折了。
# epoch:第几个epoch了。
# draw:是否要绘制图像
def threshold_optimize(predict, label, writer, fold, epoch, attack_index, draw=False):
    # 求出其中的最佳值，然后返回。
    best_res = {"probability": 0, "accuracy": 0, "precision": 0, "recall": 0, "f_score": 0}
    # 取出所有的不同的概率，然后将概率转换为0和1的predict_matrix矩阵,注意，如果种类太多，会导致GPU都存不下，所以需要少取一些，这里取步长为100好了。
    unique_probability = torch.unique(predict).reshape(-1, 1)
    # 通过步长重新选取，免得取得太多了，内存爆炸。
    unique_probability = unique_probability[::math.ceil(len(unique_probability) / config.threshold_max_classes)]
    predict_matrix = (predict >= unique_probability).add(0)
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
    best_sample_index = precision.add(recall).argmax(dim=0)
    best_res["probability"] = unique_probability[best_sample_index, 0]
    best_res["accuracy"] = accuracy[best_sample_index, 0]
    best_res["precision"] = precision[best_sample_index, 0]
    best_res["recall"] = recall[best_sample_index, 0]
    best_res["f_score"] = f_score[best_sample_index, 0]
    # 进行四种属性的绘制,每个epoch只画一次。
    if attack_index == 0 and draw:
        writer.add_scalar(f"{config.start_time}_reentry_accuracy", best_res["accuracy"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_reentry_precision", best_res["precision"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_reentry_recall", best_res["recall"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_reentry_f_score", best_res["f_score"], fold * config.epoch_size + epoch)
    elif attack_index == 1 and draw:
        writer.add_scalar(f"{config.start_time}_timestamp_accuracy", best_res["accuracy"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_timestamp_precision", best_res["precision"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_timestamp_recall", best_res["recall"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_timestamp_f_score", best_res["f_score"], fold * config.epoch_size + epoch)
    elif attack_index == 2 and draw:
        writer.add_scalar(f"{config.start_time}_arithmetic_accuracy", best_res["accuracy"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_arithmetic_precision", best_res["precision"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_arithmetic_recall", best_res["recall"], fold * config.epoch_size + epoch)
        writer.add_scalar(f"{config.start_time}_arithmetic_f_score", best_res["f_score"], fold * config.epoch_size + epoch)
    return best_res
