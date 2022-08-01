# coding=UTF-8
import os
import json
import config
import shutil


# 判断文件夹是否已经存在，如果不存在就创建文件夹
def dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


# 判断当前文件夹内容是不是空的,是空的就返回True。
def is_blank_now_dir(dir_path):
    for now_dir, child_dirs, child_files in os.walk(dir_path):
        # 采用递归的方法，先判断文件夹中是不是空的内容
        for child in child_dirs:
            is_blank_now_dir(os.path.join(now_dir, child))
        # 如果里面没有内容就删除掉。
        if len(os.listdir(now_dir)) == 0:
            os.rmdir(now_dir)
            print(f"{dir_path}由于内容已经为空，所以被删除了。")
            return True
        # 没有内容被删除的话说明是有内容的返回false，否则是True
        return False


# 获取原始的标签文件json的内容
def get_label():
    # 原始标签文件的保存地址。
    # 其中保存的格式是{"1.sol的全路径": 0, "2.sol的全路径": 0, "3.sol的全路径": 1....}
    idx_to_label_file = open(config.idx_to_label_file, 'r', encoding="UTF-8")
    label_in_memory = json.load(idx_to_label_file)
    return label_in_memory


# 创建目标文件，给定路径就行，不管中间是否有空缺的文件夹。
def create_file(file_path):
    dir_name = os.path.dirname(file_path)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    # 这里要使用a的模式，否则会导致文件原始内容会被第二次打开而删除。
    f = open(file_path, 'a', encoding="utf-8")
    f.close()


# 将某些异常的文件移动到问题文件夹中。
def remove_file(file_path):
    # 先删除json文件
    if file_path.__contains__(".json"):
        shutil.rmtree(os.path.dirname(file_path))
    # 将目标移动到智能合约源文件
    file_path = file_path.replace("AST_json", "sol_source").replace(".json", ".sol")
    # 获取源文件的项目名字路径
    dir_name = os.path.dirname(file_path)
    # 将这个源文件移动到错误文件夹中。
    shutil.move(dir_name, config.error_file_fold)


# 更新标签文件
def update_label_file(file_name, label):
    # 先判断加工以后的json文件是否存在，如果不存在，先创建内容。
    if not os.path.exists(config.idx_to_label_file):
        write_json = open(config.idx_to_label_file, 'w')
        json.dump({}, write_json)
        write_json.close()
    # 这时候一定会有的，所以可以开始更新内容了。更新以后的保存内容应该是{"文件的名字": 标签, "文件的名字": 标签....}
    read_json = open(config.idx_to_label_file, 'r', encoding="utf-8")
    # 先读取原始的内容
    origin_content = json.load(read_json)
    # 对原始的内容进行更新
    origin_content.update({file_name.replace("AST_json", "sol_source").replace(".json", ".sol"): label})
    # 关闭读取的句柄
    read_json.close()
    # 重新打开一个写入的句柄
    write_json = open(config.idx_to_label_file, 'w')
    # 将更新以后的内容重新写入到json文件当中
    json.dump(origin_content, write_json)
    # 记得关闭比句柄文件。
    write_json.close()


# 自定义的异常类，用来抛出异常。
class CustomError(Exception):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info = error_info

    def __str__(self):
        return self.error_info
