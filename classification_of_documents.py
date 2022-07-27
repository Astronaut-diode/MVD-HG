import json
import config
import os
import shutil
import utils


# 对文件进行分类归档。
def classification_of_documents():
    f = open(f"{config.idx_to_label_file}", 'r', encoding="utf-8")
    content = json.load(f)
    reen = 0
    time = 0
    arit = 0
    dele = 0
    for key in content.keys():
        # 先获取原始文件所存在的文件夹的名字
        parent_dir = os.path.basename(os.path.dirname(key))
        # 获取文件的名字
        file_name = os.path.basename(key)
        reen += content[key][0]
        # 复制文件到重入文件夹
        if content[key][0] == 1:
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.reentry_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.reentry_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key, target_file_path)
        time += content[key][1]
        # 复制文件到重入文件夹
        if content[key][1] == 1:
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.timestamp_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.timestamp_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key, target_file_path)
        arit += content[key][2]
        # 复制文件到重入文件夹
        if content[key][2] == 1:
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.arithmetic_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.arithmetic_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key, target_file_path)
        dele += content[key][3]
        # 复制文件到重入文件夹
        if content[key][3] == 1:
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.dangerous_delegate_call_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.dangerous_delegate_call_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key, target_file_path)
    print(f"重入漏洞的数量为{reen}")
    print(f"时间戳漏洞的数量为{time}")
    print(f"溢出漏洞的数量为{arit}")
    print(f"危险调用漏洞的数量为{dele}")
    print("文件都已经全部移入到对应的漏洞文件夹中")