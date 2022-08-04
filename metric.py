import numpy as np
import config
import utils


# 计算出四种漏洞的各种最优的属性
# predict:预测结果
# label:原始标签
# writer:tensor board画图用的
# fold:外面的交叉验证到哪一步了。
# epoch:交叉验证中已经到了哪一个世代了。
def score(predict, label, writer, fold, epoch):
    predict = predict.data.cpu().numpy()
    label = label.data.cpu().numpy()
    # 结果矩阵，里面存放的是四种漏洞类型的四种基础衡量标准。
    optimal_list = np.zeros((4, 4))
    # 取出第i中类型的预测结果和原始标签，输入到阈值调优中进行调优
    for attack_index in range(config.classes):
        res = threshold_optimize(predict[:, attack_index], label[:, attack_index], writer, fold, epoch)
        optimal_list[0, attack_index] = res["accuracy"]
        optimal_list[1, attack_index] = res["precision"]
        optimal_list[2, attack_index] = res["recall"]
        optimal_list[3, attack_index] = res["f_score"]
    utils.tqdm_write(optimal_list)


# 将多标签分类为多种单标签，以进行阈值调优。
def threshold_optimize(predict, label, writer, fold, epoch):
    # 求出其中的最佳值，然后返回。
    best_res = {"probability": 0, "accuracy": 0, "precision": 0, "recall": 0, "f_score": 0}
    # 取出所有的不同的概率
    probability_list = np.unique(predict)
    # 遍历其中每一个概率，求出对应的四种度量标准。
    for probability in probability_list:
        # 复制内容，避免对下一个概率的计算造成影响
        predict_tmp = predict.copy()
        label_tmp = label.copy()
        # 根据阈值，将计算出来的概率转化为标签。
        predict_tmp[predict_tmp >= probability] = 1
        predict_tmp[predict_tmp < probability] = 0
        # 根据转化以后的预测标签和原始标签，计算出混淆矩阵。
        confuse_matrix = _label_quantity(predict_tmp, label_tmp)
        accuracy = (confuse_matrix[0] + confuse_matrix[2]) / (confuse_matrix[0] + confuse_matrix[1] + confuse_matrix[2] + confuse_matrix[3])
        precision = confuse_matrix[0] / (confuse_matrix[0] + confuse_matrix[1])
        recall = confuse_matrix[0] / (confuse_matrix[0] + confuse_matrix[3])
        f_score = (1 + config.beta ** 2) * confuse_matrix[0] / ((1 + config.beta ** 2) * confuse_matrix[0] + config.beta ** 2 * confuse_matrix[3] + confuse_matrix[1] + config.epsilon)
        # 如果原始记录的内容没有当前的好，记录一下。
        if best_res["f_score"] < f_score:
            best_res["probability"] = probability
            best_res["accuracy"] = accuracy
            best_res["precision"] = precision
            best_res["recall"] = recall
            best_res["f_score"] = f_score
        # 进行四种属性的绘制。
        writer.add_scalar(f"{fold}_{epoch}_accuracy", accuracy, probability)
        writer.add_scalar(f"{fold}_{epoch}_precision", precision, probability)
        writer.add_scalar(f"{fold}_{epoch}_recall", recall, probability)
        writer.add_scalar(f"{fold}_{epoch}_f_score", f_score, probability)
    return best_res


# 根据传入的标签和原始值，计算出混淆矩阵
def _label_quantity(predict, label):
    tp = np.sum(np.logical_and(label, predict), axis=0)
    fp = np.sum(np.logical_and(1 - label, predict), axis=0)
    tn = np.sum(np.logical_and(1 - label, 1 - predict), axis=0)
    fn = np.sum(np.logical_and(label, 1 - predict), axis=0)
    return np.stack([tp, fp, tn, fn], axis=0).astype("float")
