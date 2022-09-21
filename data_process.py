import os
import shutil
import math
import random
import json
import utils


# 切割目标目录文件夹下面的内容，分到n个目标目录中。按照下面的格式输入会将data/sol_source/下面的文件夹全部分割道*/sol_source/底下去。
# 调用过程
# 1
# /home/xjj/AST-GNN/data/sol_source/
# /home/xjj/AST-GNN/*/sol_source/
# 20
def split_dir_file():
    # r"/home/xjj/data/sol_source/"
    source_dir = input("输入需要分割的目录")
    # r"/home/xjj/*/sol_source/"
    target_pattern = input("输入录入的目标目录，使用*代替需要变换的数字,会生成n个该目录，*变为1～n。")
    # 文件夹个数。
    n = input("输入需要分割为多少个子集")
    target_dir = []
    for i in range(int(n)):
        target_dir.append(target_pattern.replace("*", str(i + 1)))
    # 文件的总个数是len(os.listdir(source_dir))
    total = len(os.listdir(source_dir))
    # 计算出如果是完整的应该是多少
    average = math.ceil(total / int(n))
    # 保存每个文件夹里应该保存多少个文件
    counts = []
    # 记录前n - 1个文件夹中保存多少文件的数量和。
    sum = 0
    # 先记录完整的部分有多少个。
    for i in range(int(n) - 1):
        counts.append(average)
        sum += average
    if sum != total:
        counts.append(total - sum)
    # 每个目标文件夹为zip_dict[1],每个文件夹中需要保存多少的文件数量是zip_dict[0]
    for zip_dict in zip(counts, target_dir):
        list = os.listdir(source_dir)
        random.shuffle(list)
        # 重新循环当前的源目录，每一次进来的时候源目录的数量都是会发生变化的，因为下面用的move而不是copy。
        for index, file in enumerate(list):
            # 先判断目标目录是否存在，不存在就先创建。
            if not os.path.exists(zip_dict[1]):
                os.makedirs(zip_dict[1])
            # 如果当前文件夹个数满了，一定要及时退出，转到下一个文件夹中。
            if index == zip_dict[0]:
                break
            else:
                shutil.move(os.path.join(source_dir, file), os.path.join(zip_dict[1], file))


# 通过取出n个子集中的hash文件，删除重复的部分。
# 调用过程
# 2
# /home/xjj/AST-GNN/*/hash_to_file.json
# 20
def elimination():
    # 需要去重的文件夹中包含的hash文件的表达式，使用*表示数字循环。
    target_pattern = input("输入去重时使用目标hash文件，使用*代替需要变换的数字,会生成n个该目录，*变为1～n。")
    n = int(input("输入子集的个数"))
    hash_file_list = []
    # 记录所有需要处理的子集的hash文件地址。
    for i in range(n):
        hash_file_list.append(target_pattern.replace("*", str(i + 1)))
    total_hash = {}
    count = 0
    for hash_json_file_path in hash_file_list:
        # 根据路径获取对应的句柄
        hash_file_handle = open(hash_json_file_path, 'r')
        # 通过句柄，读取json文件中的内容
        content = json.load(hash_file_handle)
        for key in content.keys():
            if total_hash.__contains__(key):
                count += 1
                print(count, content.get(key), "可以删除了")
                shutil.rmtree(content.get(key))
            else:
                total_hash[key] = content.get(key)
    print(len(total_hash.keys()))


# 把20个小型的漏洞检测线程都运行完以后，获得了碎片结果，需要自己合并一下。运行结束以后，会出现四个文件夹，分别代表三种漏洞和没有漏洞的文件。
# 使用方法，下面是输入
# 3
# 其中对应的一个idx_to_file.json的地址。如/home/xjj/AST-GNN/*/idx_to_label.json
# 20
def classification_of_documents():
    target_pattern = input("输入标签文件地址,使用*代替数字")
    n = int(input("重复多少次"))
    file_list = []
    for i in range(n):
        file_list.append(target_pattern.replace("*", str(i + 1)))
    attack_condition = {"reentry": {"attack": 0, "suspected_attack": 0, "no_attack": 0}, "timestamp": {"attack": 0, "suspected_attack": 0, "no_attack": 0}, "arithmetic": {"attack": 0, "suspected_attack": 0, "no_attack": 0}, "fine": {"attack": 0, "suspected_attack": 0, "no_attack": 0}}
    for file in file_list:
        f = open(f"{file}", 'r', encoding="utf-8")
        content = json.load(f)
        types = ["reentry", "timestamp", "arithmetic"]
        for index, type_name in enumerate(types):
            parent_path = f"/home/xjj/AST-GNN/{type_name}"
            for key in content.keys():
                # 获取文件的名字
                file_name = os.path.basename(key)
                # 文件复制到别的文件夹中以后工程项目的名字
                dir_name = file_name[:-4]
                if content[key][index] == 1:
                    utils.dir_exists(f"{parent_path}/{dir_name}/")
                    target_file_path = f"{parent_path}/{dir_name}/{file_name}"
                    print(f"把{key}移入到{target_file_path}中")
                    try:
                        shutil.copyfile(key, target_file_path)
                    except Exception as e:
                        print(key, "有问题，跳过了")
                        continue
                    attack_condition[type_name]["attack"] += 1
            utils.tip(f"{file}中{type_name}漏洞的数量为{attack_condition[type_name]['attack']}")
            utils.success("确认有漏洞的文件都已经全部移入到对应的漏洞文件夹中。")
    for file in file_list:
        f = open(f"{file}", 'r', encoding="utf-8")
        content = json.load(f)
        parent_path = f"/home/xjj/AST-GNN/fine"
        for key in content.keys():
            # 获取文件的名字
            file_name = os.path.basename(key)
            # 文件复制到别的文件夹中以后工程项目的名字
            dir_name = file_name[:-4]
            if content[key][0] == 0 and content[key][1] == 0 and content[key][2] == 0:
                utils.dir_exists(f"{parent_path}/{dir_name}/")
                target_file_path = f"{parent_path}/{dir_name}/{file_name}"
                print(f"把{key}移入到{target_file_path}中")
                try:
                    shutil.copyfile(key, target_file_path)
                except Exception as e:
                    print(key, "有问题，跳过了")
                    continue
                attack_condition["fine"]["no_attack"] += 1
        utils.tip(f"{file}中无漏洞的数量为{attack_condition['fine']['no_attack']}")
        utils.success("确认无漏洞的文件都已经全部移入到对应的文件夹中。")


# 从原始目录中抽取任意数量的文件到目标目录中。
# 调用方式
# 4
# 源文件夹的地址
# 目标文件夹的地址
# 从源文件中要复制多少个文件目标文件夹
def extract_random_file_to_dest():
    source = input("输入原始目录")
    target = input("输入目标目录")
    n = int(input("输入文件个数"))
    list = os.listdir(source)
    random.shuffle(list)
    for index, tmp in enumerate(list):
        if index >= n:
            break
        else:
            # 获取文件的名字
            dir_name = os.path.basename(tmp)
            source_path = os.path.join(source, dir_name)
            target_path = os.path.join(target, dir_name)
            shutil.copytree(source_path, target_path)
            print(source_path, "->", target_path)


if __name__ == '__main__':
    func = input("请输入你选择的功能:")
    if func == "1":
        split_dir_file()
    if func == "2":
        elimination()
    if func == "3":
        classification_of_documents()
    if func == "4":
        extract_random_file_to_dest()
