# coding=UTF-8
import os
import re
import shutil
import utils

# 删除project_name文件夹中的每一个文件的注释，如果内容不正常直接删除。
def remove_comments(data_sol_source_project_dir_path):
    # 临时文件的存放位置
    tmp_file_name = os.path.join(data_sol_source_project_dir_path, "tmp.sol")
    # 对当前的工程文件夹进行遍历操作。
    for now_dir, child_dirs, child_files in os.walk(data_sol_source_project_dir_path):
        # 每一份代码都要单独处理。
        for file_name in child_files:
            # 如果是临时文件需要跳过该文件的处理
            if file_name == "tmp.sol":
                continue
            # 源文件的全路径
            file = os.path.join(now_dir, file_name)
            # 打开源文件和一个新文件，将源文件中的内容抄到新的文件当中去。
            utils.create_file(tmp_file_name)
            with open(file, 'r') as origin_file_handle, open(tmp_file_name, 'w') as tmp_file_handle:
                # 当前是否处于注释的状态，在遇到了/**的时候开启，在遇到了**/的时候关闭
                annotation_state = False
                try:
                    # 遍历源文件中的内容
                    for line in origin_file_handle:
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
                            # 有可能是//开头，这个时候/*是直接被忽略的
                            if len(re.findall("//", line)) > 0:
                                # 如果发现//比较考前，那就视为行注释。
                                if line.index("//") < line.index("/*"):
                                    break
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
                            tmp_file_handle.write(line[0:line.index("//")] + "\n")
                        # 如果不在注释状态，而且没有行注释，那就可以直接写到临时文件当中。
                        else:
                            tmp_file_handle.write(line)
                except Exception as e:
                    print(f'{file}因为含有不正常的内容而被删除，异常信息{e}')
            # 都已经写好了，关闭句柄文件。
            origin_file_handle.close()
            tmp_file_handle.close()
            # 删除源文件
            os.remove(file)
            # 将临时文件的文件名移动到对应的位置上，实现覆写。
            shutil.move(tmp_file_name, file)
            print(f"{file}注释删除完毕")
