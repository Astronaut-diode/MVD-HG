import numpy as np
import config
import utils

# modified from https://github.com/yl2019lw/ImPloc/blob/revision/util/npmetrics.py

epsilon = 1e-8  # to aviod zero-divison


# Example-based metrics

# label (numpy boolean) shape: N x nlabel
# predict (numpy boolean) shape: N x nlabel
def example_subset_accuracy(label, predict):
    ex_equal = np.all(np.equal(label, predict), axis=1).astype("float32")
    return np.mean(ex_equal)


def example_accuracy(label, predict):
    ex_and = np.sum(np.logical_and(label, predict), axis=1).astype("float32")
    ex_or = np.sum(np.logical_or(label, predict), axis=1).astype("float32")
    return np.mean(ex_and / (ex_or + epsilon))


def example_precision(label, predict):
    ex_and = np.sum(np.logical_and(label, predict), axis=1).astype("float32")
    ex_predict = np.sum(predict, axis=1).astype("float32")
    return np.mean(ex_and / (ex_predict + epsilon))


def example_recall(label, predict):
    ex_and = np.sum(np.logical_and(label, predict), axis=1).astype("float32")
    ex_label = np.sum(label, axis=1).astype("float32")
    return np.mean(ex_and / (ex_label + epsilon))


def example_f1(label, predict, beta=1):
    p = example_precision(label, predict)
    r = example_recall(label, predict)
    return ((1 + beta ** 2) * p * r) / ((beta ** 2) * (p + r + epsilon))


# Label-based metrics

def _label_quantity(label, predict):
    tp = np.sum(np.logical_and(label, predict), axis=0)
    fp = np.sum(np.logical_and(1 - label, predict), axis=0)
    tn = np.sum(np.logical_and(1 - label, 1 - predict), axis=0)
    fn = np.sum(np.logical_and(label, 1 - predict), axis=0)
    return np.stack([tp, fp, tn, fn], axis=0).astype("float")


def cal_base_metric(label, predict, beta=1):
    quantity = _label_quantity(label, predict)
    print(f"\nAccuracy:{(quantity[0] + quantity[2]) / (quantity[0] + quantity[1] + quantity[2] + quantity[3])}")
    print(f"Precision:{quantity[0] / (quantity[0] + quantity[1])}")
    print(f"Recall:{quantity[0] / (quantity[0] + quantity[3])}")
    print(f"F-Score:{(1 + beta ** 2) * quantity[0] / ((1 + beta ** 2) * quantity[0] + beta ** 2 * quantity[3] + quantity[1] + epsilon)}")


def label_accuracy_macro(label, predict):
    quantity = _label_quantity(label, predict)
    tp_tn = np.add(quantity[0], quantity[2])
    tp_fp_tn_fn = np.sum(quantity, axis=0)
    return np.mean(tp_tn / (tp_fp_tn_fn + epsilon))


def label_accuracy_micro(label, predict):
    quantity = _label_quantity(label, predict)
    sum_tp, sum_fp, sum_tn, sum_fn = np.sum(quantity, axis=1)
    return (sum_tp + sum_tn) / (
            sum_tp + sum_fp + sum_tn + sum_fn + epsilon)


def label_precision_macro(label, predict):
    quantity = _label_quantity(label, predict)
    tp = quantity[0]
    tp_fp = np.add(quantity[0], quantity[1])
    return np.mean(tp / (tp_fp + epsilon))


def label_precision_micro(label, predict):
    quantity = _label_quantity(label, predict)
    sum_tp, sum_fp, sum_tn, sum_fn = np.sum(quantity, axis=1)
    return sum_tp / (sum_tp + sum_fp + epsilon)


def label_recall_macro(label, predict):
    quantity = _label_quantity(label, predict)
    tp = quantity[0]
    tp_fn = np.add(quantity[0], quantity[3])
    return np.mean(tp / (tp_fn + epsilon))


def label_recall_micro(label, predict):
    quantity = _label_quantity(label, predict)
    sum_tp, sum_fp, sum_tn, sum_fn = np.sum(quantity, axis=1)
    return sum_tp / (sum_tp + sum_fn + epsilon)


def label_f1_macro(label, predict, beta=1):
    quantity = _label_quantity(label, predict)
    tp = quantity[0]
    fp = quantity[1]
    fn = quantity[3]
    return np.mean((1 + beta ** 2) * tp / ((1 + beta ** 2) * tp + beta ** 2 * fn + fp + epsilon))


def label_f1_micro(label, predict, beta=1):
    quantity = _label_quantity(label, predict)
    tp = np.sum(quantity[0])
    fp = np.sum(quantity[1])
    fn = np.sum(quantity[3])
    return (1 + beta ** 2) * tp / ((1 + beta ** 2) * tp + beta ** 2 * fn + fp + epsilon)


def metric(predict, label, count, writer):
    predict = predict.data.cpu().numpy()
    label = label.data.cpu().numpy()
    predict[predict >= config.valid_threshold] = 1
    predict[predict < config.valid_threshold] = 0
    # subset_acc = example_subset_accuracy(label, predict)
    # ex_acc = example_accuracy(label, predict)
    # ex_precision = example_precision(label, predict)
    # ex_recall = example_recall(label, predict)
    # ex_f1 = example_f1(label, predict)

    lab_acc_ma = label_accuracy_macro(label, predict)
    lab_acc_mi = label_accuracy_micro(label, predict)
    lab_precision_ma = label_precision_macro(label, predict)
    lab_precision_mi = label_precision_micro(label, predict)
    lab_recall_ma = label_recall_macro(label, predict)
    lab_recall_mi = label_recall_micro(label, predict)
    lab_f1_ma = label_f1_macro(label, predict)
    lab_f1_mi = label_f1_micro(label, predict)
    cal_base_metric(label, predict)
    # print("subset acc:        %.4f" % subset_acc)
    # print("example acc:       %.4f" % ex_acc)
    # print("example precision: %.4f" % ex_precision)
    # print("example recall:    %.4f" % ex_recall)
    # print("example f1:        %.4f" % ex_f1)
    print("label acc macro:   %.4f" % lab_acc_ma)
    print("label acc micro:   %.4f" % lab_acc_mi)
    print("label prec macro:  %.4f" % lab_precision_ma)
    print("label prec micro:  %.4f" % lab_precision_mi)
    print("label rec macro:   %.4f" % lab_recall_ma)
    print("label rec micro:   %.4f" % lab_recall_mi)
    print("label f1 macro:    %.4f" % lab_f1_ma)
    print("label f1 micro:    %.4f" % lab_f1_mi)
    writer.add_scalar("label acc macro:", lab_acc_ma, count)
    writer.add_scalar("label acc micro:", lab_acc_ma, count)
    writer.add_scalar("label prec macro:", lab_acc_ma, count)
    writer.add_scalar("label prec micro:", lab_acc_ma, count)
    writer.add_scalar("label rec macro:", lab_acc_ma, count)
    writer.add_scalar("label rec micro:", lab_acc_ma, count)
    writer.add_scalar("label f1 macro:", lab_acc_ma, count)
    writer.add_scalar("label f1 micro:", lab_acc_ma, count)

