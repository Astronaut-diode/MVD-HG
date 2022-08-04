import os
import json
import re
import hashlib
import utils
import config


def get_char(group, source_dict):
    group = group.lower()
    for char in list(group):
        source_dict[char] += 1


# 计算出工程项目的hash值，如果工程项目的hash值已经存在了，那就代表出现了重复，不操作当前文件，返回True。
# 否则记录当前工程项目的hash值，并返回False。
def has_equal_hash(dir_path):
    # 如果是第二趟，那就不用操作了，没有必要。
    if config.create_corpus_mode == "generate_all":
        return False
    utils.create_file(config.hash_to_file)
    source_dict = {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0, 'k': 0,
                   'l': 0, 'm': 0, 'n': 0, 'o': 0, 'p': 0, 'q': 0, 'r': 0, 's': 0, 't': 0, 'u': 0, 'v': 0,
                   'w': 0, 'x': 0, 'y': 0, 'z': 0}
    pattern = re.compile(r"[a-zA-Z]+")
    source_str = ""
    for now_dir, dir_childes, file_childes in os.walk(dir_path):
        for file in file_childes:
            f = open(f"{now_dir}/{file}", "r", encoding="UTF-8")
            for line in f.readlines():
                # 通过正则获取其中所有的字母，然后使用函数，为字典的字母中增加数量。
                res = re.findall(pattern, line)
                for group in res:
                    get_char(group, source_dict)
            f.close()
    for key in source_dict.keys():
        source_str += f"{key}{source_dict[key]}"
    # 根据组成的字符串计算出来的hash值。
    file_hash = hashlib.sha224(source_str.encode("utf-8")).hexdigest()
    # 先判断加工以后的json文件是否存在，如果不存在，先创建内容。
    if not os.path.exists(config.hash_to_file):
        write_json = open(config.hash_to_file, 'w')
        json.dump({}, write_json)
        write_json.close()
    # 这时候一定会有的，所以可以开始更新内容了。更新以后的保存内容应该是{"文件的名字": 标签, "文件的名字": 标签....}
    read_json = open(config.hash_to_file, 'r', encoding="utf-8")
    # 先读取原始的内容
    origin_content = json.load(read_json)
    # 如果原始的hash值已经存在了，那就代表是出现了重复，不进行操作，关闭文件句柄即可。
    if file_hash in origin_content.keys():
        read_json.close()
        return True
    else:
        # 对原始的内容进行更新
        origin_content.update({file_hash: dir_path})
        # 关闭读取的句柄
        read_json.close()
        # 重新打开一个写入的句柄
        write_json = open(config.idx_to_label_file, 'w')
        # 将更新以后的内容重新写入到json文件当中
        json.dump(origin_content, write_json)
        # 记得关闭比句柄文件。
        write_json.close()
        return False
