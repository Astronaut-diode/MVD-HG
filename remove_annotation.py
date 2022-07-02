import os
import re

# 在linux环境下的当前工程路径:/home/xjj
parent_path = os.getcwd()
# 在data目录下，原始的solidity保存的目录:/home/xjj/AST-GNN/data/sol_source/
data_sol_source_dir_path = parent_path + "/data/sol_source/"


# 删除源代码中的注释部分
def remove_annotation():
    # 循环遍历所有的工程文件夹
    for project_name in os.listdir(data_sol_source_dir_path):
        # 截止到工程文件夹为止:/home/xjj/AST-GNN/data/sol_source/project_name/
        data_sol_source_dir_project_path = data_sol_source_dir_path + project_name + "/"
        # 遍历工程文件夹下面的所有文件
        for file_name in os.listdir(data_sol_source_dir_project_path):
            # 源文件的全路径
            file = data_sol_source_dir_project_path + file_name
            # 打开源文件和一个新文件，将源文件中的内容抄到新的文件当中去。
            with open(file, 'r') as origin_file, open(data_sol_source_dir_project_path + "tmp.sol", 'w') as tmp_file:
                # 当前是否处于注释的状态，在遇到了/**的时候开启，在遇到了**/的时候关闭
                annotation_state = False
                # 遍历源文件中的内容
                for line in origin_file:
                    # 如果注释状态是开着的，那就需要去找关闭状态
                    if annotation_state:
                        # 如果发现了其中是含有*/的，那就说明可以关闭注释状态了
                        if len(re.findall("\\*/", line)) > 0:
                            # 在*/这个之后的部分是要记录下来的
                            line = line[line.index("*/") + 2:]
                            annotation_state = False
                        # 否则代表这一行都是注释，直接略过。
                        else:
                            continue
                    # 说明当前行是存在/**注释的，可以先打开注解模式,如果同一行中有多个段注释，需要采用while才能删除
                    while len(re.findall("/\\*", line)) > 0:
                        annotation_state = True
                        # 如果发现在这一行就结束了段注释，那么要及时的关闭的注释状态
                        if len(re.findall("\\*/", line)) > 0:
                            # 删除本行中的/*和*/中的部分，其余的部分不受影响。
                            line = line.replace(line[line.index("/*"): line.index("*/") + 2], "")
                            # 关闭注释状态，如果本行还有段注释，后面还会重新开启的
                            annotation_state = False
                        # 如果本行中没有结尾的段注释符号，直接跳过
                        else:
                            break
                    # 如果是注释状态跳出的while循环，直接略过
                    if annotation_state:
                        continue
                    # 如果存在的不是段注释的模式，而是行注释
                    if len(re.findall("//", line)) > 0:
                        tmp_file.write(line[0:line.index("//")])
                    # 如果不在注释状态，而且没有行注释，那就可以直接写到临时文件当中。
                    else:
                        tmp_file.write(line)
            # 删除源文件
            os.remove(file)
            # 将临时文件的文件名改成源文件，实现覆写功能
            os.rename(data_sol_source_dir_project_path + "tmp.sol", file)
