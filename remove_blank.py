import config
import os
import json


# 删除空白行
def remove_blank_line(data_sol_source_project_dir_path):
    # 如果不是这创建所有的字符库的步骤，更笨没有必要去修改文件。
    if config.run_mode != "create" or config.create_corpus_mode != "create_corpus_txt" or config.create_code_snippet or config.data_augmentation:
        return
    # 对当前的工程文件夹进行遍历操作。
    for now_dir, child_dirs, child_files in os.walk(data_sol_source_project_dir_path):
        # 每一份代码都要单独处理。
        for file_name in child_files:
            # 源文件的全路径
            target_file = os.path.join(now_dir, file_name)
            # 开始读取内容准备开始删除空白行
            handle = open(target_file, 'r')
            readlines = handle.readlines()
            handle.close()
            # 代表每一行都有多少的偏差量，目前全部都还是0，也即没有偏差
            diff_line = [0]
            # 重新写入目标文件，但是这次要删除空行。
            handle = open(target_file, 'w')
            for index, line in enumerate(readlines):
                # 如果仅仅是空行，那么当前行的偏差量就要加1,否则说明当前行不需要增加偏移量
                if line == "\n":
                    diff_line[-1] -= 1
                else:
                    handle.write(line)
                diff_line.append(diff_line[-1])
            handle.close()
            # 读取行级别漏洞标签文件
            line_file_path = config.data_dir_path + "/solidifi_labels.json"
            # 只有行级别标签文件存在的时候才需要更改标签
            if os.path.exists(line_file_path):
                origin_line_file = open(line_file_path, 'r')
                origin_line_content = json.load(origin_line_file)
                # 根据原始行推演插入以后的目标行。
                res = []
                for vul_line in origin_line_content[file_name][config.attack_type_name]:
                    res.append(diff_line[vul_line] + vul_line)
                origin_line_content[file_name] = {config.attack_type_name: res}
                origin_line_file.close()
                # 重新打开一个写入的句柄,并将修改以后的内容写入到文件当中去
                write_json = open(line_file_path, 'w')
                json.dump(origin_line_content, write_json)
                write_json.close()