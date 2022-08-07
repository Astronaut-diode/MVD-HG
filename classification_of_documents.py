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
    suspected_reen = 0
    suspected_time = 0
    suspected_arit = 0
    for key in content.keys():
        # 先获取原始文件所存在的文件夹的名字
        parent_dir = os.path.basename(os.path.dirname(key))
        # 获取文件的名字
        file_name = os.path.basename(key)
        # 复制文件到重入文件夹
        if content[key][0] == 1:
            reen += 1
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.reentry_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.reentry_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
        # 放入到疑似重入文件夹中。
        elif content[key][0] == 2:
            suspected_reen += 1
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.suspected_reentry_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.suspected_reentry_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
        # 复制文件到重入文件夹
        if content[key][1] == 1:
            time += content[key][1]
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.timestamp_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.timestamp_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
        # 放置到疑似时间戳漏洞文件夹中
        elif content[key][1] == 2:
            suspected_time += 1
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.suspected_timestamp_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.suspected_timestamp_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
        # 复制文件到重入文件夹
        if content[key][2] == 1:
            arit += content[key][2]
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.arithmetic_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.arithmetic_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
        # 复制文件到疑似溢出文件夹
        elif content[key][2] == 2:
            suspected_arit += 1
            # 根据文件夹名字和重入攻击的文件夹路径，可以得到新的重入攻击的全路径。
            utils.dir_exists(f"{config.suspected_arithmetic_attack_fold}/{parent_dir}/")
            # 新文件的全路径
            target_file_path = f"{config.suspected_arithmetic_attack_fold}/{parent_dir}/{file_name}"
            # 复制文件到新目录中。
            shutil.copyfile(key.replace("sol_source", "complete"), target_file_path)
    utils.tip(f"重入漏洞的数量为{reen}")
    utils.tip(f"疑似重入漏洞的数量为{suspected_reen}")
    utils.tip(f"时间戳漏洞的数量为{time}")
    utils.tip(f"疑似时间戳漏洞的数量为{suspected_time}")
    utils.tip(f"溢出漏洞的数量为{arit}")
    utils.tip(f"疑似溢出漏洞的数量为{suspected_arit}")
    utils.success("确认有漏洞的文件都已经全部移入到对应的漏洞文件夹中。")
