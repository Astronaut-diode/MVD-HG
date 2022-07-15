# coding=UTF-8
import os
import json
import config


# 判断文件夹是否已经存在，如果不存在就创建文件夹
def dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)


# 判断当前文件夹内容是不是空的,是空的就返回True。
def is_blank_now_dir(dir_path):
    if len(os.listdir(dir_path)) == 0:
        print(f"{dir_path}由于内容已经为空，所以被删除了。")
        return True
    else:
        return False


# 获取原始的标签文件json的内容
def get_label():
    # 原始标签文件的保存地址。
    # 其中保存的格式是[{"0": 0}, {"1": 0}, {"2": 1}....]
    idx_to_label_file = open(config.idx_to_label_file, 'r', encoding="UTF-8")
    label_in_memory = json.load(idx_to_label_file)
    return label_in_memory


def update_sol_to_label(obj):
    # 先判断加工以后的json文件是否存在，如果不存在，先创建内容。
    if not os.path.exists(config.sol_to_label_file):
        write_json = open(config.sol_to_label_file, 'w')
        json.dump({}, write_json)
        write_json.close()
    # 这时候一定会有的，所以可以开始更新内容了。更新以后的保存内容应该是{"文件的名字": 标签, "文件的名字": 标签....}
    read_json = open(config.sol_to_label_file, 'r', encoding="utf-8")
    # 先读取原始的内容
    origin_content = json.load(read_json)
    # 对原始的内容进行更新
    origin_content.update(obj)
    # 关闭读取的句柄
    read_json.close()
    # 重新打开一个写入的句柄
    write_json = open(config.sol_to_label_file, 'w')
    # 将更新以后的内容重新写入到json文件当中
    json.dump(origin_content, write_json)
    # 记得古纳比句柄文件。
    write_json.close()
