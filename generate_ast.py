# coding=UTF-8
import os
import re
import config

# 在linux环境下的当前工程路径
parent_path = os.getcwd()
# 在data目录下，原始的solidity保存的目录
data_sol_source_dir_path = parent_path + "/data/sol_source/"
# 在data目录下，生成的ast的json文件的保存目录
data_ast_json_dir_path = parent_path + "/data/AST_json/"


# 给定源代码，将源代码转化为抽象语法树
def generate_ast():
    # 编译器的文件路径
    solc_dir_path = config.compile_dir_path
    # 循环/home/xjj/AST-GNN/data/sol_source/文件夹中每一个工程项目
    for project_dir_name in os.listdir(data_sol_source_dir_path):
        # 需要编译的项目的全路径，如"/home/xjj/AST-GNN/data/sol_source/project_name/"，这里直接到了项目文件夹级别
        data_sol_source_project_dir_path = data_sol_source_dir_path + project_dir_name + "/"
        # 遍历项目文件夹中的每一个文件
        for file_name in os.listdir(data_sol_source_project_dir_path):
            # 需要操作的源代码的文件全路径，如"/home/xjj/AST-GNN/data/sol_source/project_name/file_name.sol",这里代表了文件的名字，已经到了文件级别
            full_compile_file_path = data_sol_source_project_dir_path + file_name
            # 保存所有的版本号
            versions = []
            # 读取当前这个文件的版本号，判断是否含有对应的编译器
            with open(full_compile_file_path, 'r') as file_content:
                # 对源文件中的每一行进行循环遍历，因为一个文件中可能包含有多个编译器版本。比如在/home/xjj/AST-GNN/sol_example/multi_compile.sol
                for line in file_content.readlines():
                    # 对其中的每一行使用正则语句进行匹配
                    ans = re.findall(config.version_match_rule, line)
                    # 如果有匹配上的，那就需要取出其中的版本号。
                    if len(ans) > 0:
                        # 版本号的写法一共有两种
                        # pragma solidity ^0.4.9;
                        # pragma solidity >=0.4.9;
                        version_tmp = ans[0].replace("pragma solidity ", "")
                        version_tmp = version_tmp.replace(">", "")
                        version_tmp = version_tmp.replace("=", "")
                        version_tmp = version_tmp.replace("^", "")
                        versions.append(version_tmp)
            # 对这个版本的列表进行排序，然后返回最大版本号进行编译。
            version = get_max_version(versions)
            # 设根据版本号以及一些已知的信息，可以构建出出命令。
            cmd = solc_dir_path + "solc-" + version + " " + full_compile_file_path + " --combined-json ast --allow-paths " + full_compile_file_path + " --ast-compact-json"
            if config.print_compile_cmd:
                print(cmd)
            # 判断是否有满足条件的编译器
            allow_flag = False
            # 查看有哪些编译器版本可用，如果不存在可用的需要重新下载
            for allow_version in os.listdir(solc_dir_path):
                # 如果包含可以使用的版本，那么可以直接编译，否则需要提示先下载对应的编译器
                if allow_version.__contains__(version):
                    allow_flag = True
                    break
            # 允许直接生成抽象语法树的情况
            if allow_flag:
                # 如果存放对应的抽象语法树的ast文件还不存在
                if not os.path.exists(data_ast_json_dir_path + project_dir_name + "/"):
                    # 创建对应的文件夹，后面再保存其中的内容。
                    os.mkdir(data_ast_json_dir_path + project_dir_name + "/")
                # 注意，文件已经存在的时候不会刷新文件，所以如果文件出错了需要手动删除掉。
                # 执行编译的命令，使用popen可以保证内容不会直接输出到控制台上，否则太多了。
                f = os.popen(cmd, 'r')
                # 打开保存的json文件，然后将内容写进去。
                with open(data_ast_json_dir_path + project_dir_name + "/" + file_name.replace(".sol", ".json"), 'w') as write_file:
                    # 逐行的将内容写到json文件当中。
                    for line in f.readlines():
                        write_file.write(line)
                # 返回的操作码
                opcode = f.close()
                # 有返回码，说明有问题，那就删除源文件和生成的json文件
                if not opcode is None:
                    os.remove(data_ast_json_dir_path + project_dir_name + "/" + file_name.replace(".sol", ".json"))
                    os.remove(data_sol_source_dir_path + project_dir_name + "/" + file_name)
                    print(data_sol_source_dir_path + project_dir_name + "/" + file_name, "由于编译过程有问题删除")
                else:
                    print(data_sol_source_dir_path + project_dir_name + "/" + file_name, "编译完成")
            else:
                # 如果是这种版本，就说明没有找到对应的版本号，直接删除完事
                not_exist_versions = ["0.0.0", "0.1.0", "0.4.0", "0.4.1", "0.4.2", "0.4.3", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.4.9", "0.4.10"]
                if version in not_exist_versions:
                    os.remove(data_sol_source_dir_path + project_dir_name + "/" + file_name)
                    print(data_sol_source_dir_path + project_dir_name + "/" + file_name, "由于无效版本号被删除")
                else:
                    # 将所有缺乏的版本的号码，输出到一个txt文件中，到时候方便一次性安装。
                    with open("/home/xjj/AST-GNN/data/absent_version_cmd.txt", 'a') as write_file:
                        write_file.write("solc-select install" + version + "\n")
                    write_file.close()
                    print(full_compile_file_path + "====>", "缺少编译器版本，请在对应的虚拟环境中安装，使用命令====>", "solc-select install", version)


# 获取数组中最大的版本号
def get_max_version(versions):
    # 最大的大版本号
    big_version = 0
    # 遍历所有的版本号，找到其中最大的一个大版本
    for version in versions:
        # 取出对应的大版本
        big = version.split(".")[1]
        # 如果取出的大版本大于当前的最大记录，那就记录下来
        if int(big) >= int(big_version):
            big_version = big
    # 最大的大版本下最大的小版本
    small_version = 0
    # 遍历其中的版本，为了获取小版本
    for version in versions:
        # 先拆分字符串，是为了同时获取大版本和小版本
        res = version.split(".")
        big = res[1]
        # 如果取出的大版本和刚刚记录的最大的大版本一致，才能进去判断谁是最大的小版本。
        if int(big) == int(big_version):
            # 取出小版本。
            small = res[2]
            # 如果小版本的内容大于最大的小版本，记录下来。
            if int(small) >= int(small_version):
                small_version = small
    # 最终返回构造好的最大版本号。
    return "0." + str(big_version) + "." + str(small_version)