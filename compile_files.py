# coding=UTF-8
import os
import re
import config
import utils


def compile_files(data_sol_source_project_dir_path, data_ast_json_project_dir_path):
    # 如果是generate_all，可以不走这个函数了，因为一开始create_corpus_txt的时候已经走过了。
    if config.create_corpus_mode == "generate_all":
        return
    # 遍历工程文件夹下面的每一个文件。
    for now_dir, child_dirs, child_files in os.walk(data_sol_source_project_dir_path):
        # 遍历项目文件夹中的每一个文件
        for file_name in child_files:
            # 需要操作的源代码的文件全路径，如"/home/xjj/AST-GNN/data/sol_source/project_name/file_name.sol",这里代表了文件的名字，已经到了文件级别
            full_compile_file_path = os.path.join(now_dir, file_name)
            # 保存的json文件的全路径,如"/home/xjj/AST-GNN/data/AST_json/project_name/file_name.json",这里代表了文件的名字，已经到了文件级别
            full_compile_target_path = full_compile_file_path.replace("sol_source", "AST_json").replace(".sol", ".json")
            # 获取当前文件的版本号。
            version = get_file_version(full_compile_file_path)
            # 设根据版本号以及一些已知的信息，可以构建出出命令。
            cmd = config.compile_dir_path + "solc-" + version + " " + full_compile_file_path + " --combined-json ast --allow-paths " + full_compile_file_path + " --ast-compact-json"
            utils.tip(cmd)
            # 判断是否有满足条件的编译器
            allow_flag = False
            # 查看有哪些编译器版本可用，如果不存在可用的需要重新下载
            for allow_version in os.listdir(config.compile_dir_path):
                # 如果包含可以使用的版本，那么可以直接编译，否则需要提示先下载对应的编译器
                if allow_version.__contains__(version):
                    allow_flag = True
                    break
            # 允许直接生成抽象语法树的情况
            if allow_flag:
                # 如果存放对应的抽象语法树的ast文件还不存在
                utils.dir_exists(data_ast_json_project_dir_path)
                # 注意，文件已经存在的时候不会刷新文件，所以如果文件出错了需要手动删除掉。
                # 执行编译的命令，使用popen可以保证内容不会直接输出到控制台上，否则太多了。
                f = os.popen(cmd, 'r')
                # 打开保存的json文件，然后将内容写进去。
                utils.create_file(full_compile_target_path)
                with open(full_compile_target_path, 'w') as write_file:
                    # 逐行的将内容写到json文件当中。
                    for line in f.readlines():
                        write_file.write(line)
                # 返回的操作码
                opcode = f.close()
                # 有返回码，说明有问题，那就删除源文件和生成的json文件
                if opcode is not None:
                    # 只需要传入json的名字，就会连同sol一起删除。
                    utils.remove_file(full_compile_target_path)
                    utils.error(f"{full_compile_file_path}由于编译过程有问题删除")
                else:
                    utils.success(f"{full_compile_file_path}编译完成")
            else:
                # 如果是这种版本，就说明没有找到对应的版本号，直接删除完事
                not_exist_versions = ["0.0.0", "0.1.0", "0.4.0", "0.4.1", "0.4.2", "0.4.3", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.4.9", "0.4.10"]
                if version in not_exist_versions:
                    utils.remove_file(full_compile_file_path)
                    utils.error(f"{full_compile_file_path}由于无效版本号被删除")
                else:
                    # 将所有缺乏的版本的号码，输出到一个txt文件中，到时候方便一次性安装。
                    with open(config.absent_version_cmd_file, 'a') as write_file:
                        write_file.write("solc-select install" + version + "\n")
                    write_file.close()
                    utils.remove_file(full_compile_file_path)
                    utils.error(f"{full_compile_file_path}====> 缺少编译器版本，请在对应的虚拟环境中安装，使用命令====> solc-select install {version} 但是我差不多都有了，现在就直接删除好了。")
    # 结束的时候对AST_json中的工程文件夹进行判断，如果里面含有空的文件夹，删除掉。
    utils.is_blank_now_dir(data_ast_json_project_dir_path)


# 获取当前文件的适用编译版本。
def get_file_version(full_compile_file_path):
    # 保存所有的版本号
    versions = []
    # 读取当前这个文件的版本号，判断是否含有对应的编译器
    with open(full_compile_file_path, 'r') as file_content:
        # 对源文件中的每一行进行循环遍历，因为一个文件中可能包含有多个编译器版本。比如在/home/xjj/AST-GNN/sol_example/multi_compile.sol
        for line in file_content.readlines():
            # 判断当前行是否是代表版本号码的一行。
            ans = re.search(config.version_match_rule, line)
            # 如果有匹配上的，那就需要取出其中的版本号，也就是说当前行是pragma solidity ^xxx等。
            if ans:
                res = get_versions(ans.group())
                # res有可能是个空的列表，因为给出的版本号是找不到的。
                if len(res):
                    # 根据这一行pragma中的代码，判断可以用的版本号有哪些，待会一股脑进行计算谁可以使用。
                    versions.append(res)
            # 进行引用匹配，查看是否有引用其他文件。
            pattern = "import \'?\"?[@.\\/\\w]*\'?\"?;"
            import_re = re.findall(pattern, line)
            # 说明确实存在引用的情况。
            if len(import_re) > 0:
                # 取出其中的地址。
                address = import_re[0].replace("import", "").replace("'", "").replace("\"", "").replace(";", "").replace(" ", "")
                if address[0] != ".":
                    address = f"./{address}"
                # 获取调用文件的最大编译版本。
                versions.append(get_file_version(os.path.join(os.path.dirname(full_compile_file_path), address)))
    # 返回所有的编译版本中最大的一个，是因为一个文件中可能会有多个最大版本。
    return get_max_version(versions)


# 获取pragma中应该使用的版本号,返回的是列表，代表针对这个pragma语句来说，这个列表中的版本都可以使用。
def get_versions(pragma):
    # 用来记录的哪个版本出现了多少次的hash表
    version_hash = {"0.4.0": 0, "0.4.1": 0, "0.4.2": 0, "0.4.3": 0, "0.4.4": 0, "0.4.5": 0, "0.4.6": 0, "0.4.7": 0, "0.4.8": 0, "0.4.9": 0, "0.4.10": 0,
                    "0.4.11": 0, "0.4.12": 0, "0.4.13": 0, "0.4.14": 0, "0.4.15": 0, "0.4.16": 0, "0.4.17": 0, "0.4.18": 0, "0.4.19": 0, "0.4.20": 0,
                    "0.4.21": 0, "0.4.22": 0, "0.4.23": 0, "0.4.24": 0, "0.4.25": 0, "0.4.26": 0, "0.5.0": 0, "0.5.1": 0, "0.5.2": 0, "0.5.3": 0, "0.5.4": 0,
                    "0.5.5": 0, "0.5.6": 0, "0.5.7": 0, "0.5.8": 0, "0.5.9": 0, "0.5.10": 0, "0.5.11": 0, "0.5.12": 0, "0.5.13": 0, "0.5.14": 0, "0.5.15": 0,
                    "0.5.16": 0, "0.5.17": 0, "0.6.0": 0, "0.6.1": 0, "0.6.2": 0, "0.6.3": 0, "0.6.4": 0, "0.6.5": 0, "0.6.6": 0, "0.6.7": 0, "0.6.8": 0, "0.6.9": 0,
                    "0.6.10": 0, "0.6.11": 0, "0.6.12": 0, "0.7.0": 0, "0.7.1": 0, "0.7.2": 0, "0.7.3": 0, "0.7.4": 0, "0.7.5": 0, "0.7.6": 0, "0.8.0": 0, "0.8.1": 0,
                    "0.8.2": 0, "0.8.3": 0, "0.8.4": 0, "0.8.5": 0, "0.8.6": 0, "0.8.7": 0, "0.8.8": 0, "0.8.9": 0, "0.8.10": 0, "0.8.11": 0, "0.8.12": 0, "0.8.13": 0,
                    "0.8.14": 0, "0.8.15": 0}
    # 先对原始语句进行一定的预处理。
    pragma = pragma.replace(" ", "").replace("pragma", "").replace("solidity", "").replace(";", "")
    # 记录特殊符号一共出现了几次，也就是有几种判定条件。
    flag = 0
    # 先查询是否存在^
    up_re = re.findall(r"\^[\w\\.]*", pragma)
    # 如果^确实存在，对其进行操作，获取其版本号，然后修改上面的hash表。
    if len(up_re) != 0:
        # 增加判定条件的数量。
        flag += 1
        # 获取之前查询出来的版本号。
        floor_version = re.findall(r"[\w\\.]+", up_re[0])[0]
        # 有的版本号会写成0.5.01,0.5.00这种，所以需要特殊处理
        tmp = floor_version.split(".")
        res = f"{tmp[0]}.{tmp[1]}."
        if len(tmp[2]) == 2 and tmp[2][0] == "0":
            floor_version = f"{res}{tmp[2][1]}"
        else:
            floor_version = f"{res}{tmp[2]}"
        if floor_version in config.versions:
            # 将这个版本号作为最低的版本号。
            floor_index = config.versions.index(floor_version)
        else:
            return []
        # 匹配大版本的模式串
        pattern = "..."
        # 因为是^所以可以一直往后取。
        for i in config.versions[floor_index:]:
            if re.search(pattern, i)[0] == re.search(pattern, floor_version)[0]:
                version_hash[i] += 1
    big_re = re.findall(r">[\w\\.=]*", pragma)
    if len(big_re) != 0:
        flag += 1
        floor_version = re.findall(r"[\w\\.]+", big_re[0])[0]
        floor_index = config.versions.index(floor_version)
        # 匹配大版本的模式串
        pattern = "..."
        # 如果含有等号，那等号的版本需要带上。
        if big_re[0].__contains__("="):
            # 因为是>所以可以一直往后取。
            for i in config.versions[floor_index:]:
                if re.search(pattern, i)[0] == re.search(pattern, floor_version)[0]:
                    version_hash[i] += 1
        else:
            # 因为是>所以可以一直往后取。
            for i in config.versions[floor_index + 1:]:
                if re.search(pattern, i)[0] == re.search(pattern, floor_version)[0]:
                    version_hash[i] += 1
    small_re = re.findall(r"<[\w\\.=]*", pragma)
    if len(small_re) != 0:
        flag += 1
        floor_version = re.findall(r"[\w\\.]+", small_re[0])[0]
        floor_index = config.versions.index(floor_version)
        # 如果含有等号，那等号的版本需要带上。
        if small_re[0].__contains__("="):
            for i in config.versions[floor_index::-1]:
                version_hash[i] += 1
        else:
            for i in config.versions[floor_index - 1::-1]:
                version_hash[i] += 1
    # 如果一个标签都没有，说明是固定版本的，直接使用对应版本。
    if flag == 0:
        return [pragma.replace("pragma", "").replace("solidity", "").replace(" ", "").replace(";", "")]
    res = []
    # 这个hash表中，第一个满足条件的可以直接拿来用,注意，一定要从0.4.12开始,因为0.4.0到0.4.10没有编译器，而0.4.11又不能用某一个命令。
    for item in list(version_hash.keys())[::-1]:
        if version_hash[item] == flag:
            res.append(item)
    return res


# 获取数组中最大的版本号，这里的versions是一个二维数组，[[0.4.0, 0.4.1], [0.5.0, 0.5.1, 0.5.2,...]]这样，需要求出公共部分
def get_max_version(versions):
    # 如果没有版本号，使用0.4.26
    if len(versions) == 0:
        return "0.4.26"
    version_hash = {"0.4.0": 0, "0.4.1": 0, "0.4.2": 0, "0.4.3": 0, "0.4.4": 0, "0.4.5": 0, "0.4.6": 0, "0.4.7": 0, "0.4.8": 0, "0.4.9": 0, "0.4.10": 0,
                    "0.4.11": 0, "0.4.12": 0, "0.4.13": 0, "0.4.14": 0, "0.4.15": 0, "0.4.16": 0, "0.4.17": 0, "0.4.18": 0, "0.4.19": 0, "0.4.20": 0,
                    "0.4.21": 0, "0.4.22": 0, "0.4.23": 0, "0.4.24": 0, "0.4.25": 0, "0.4.26": 0, "0.5.0": 0, "0.5.1": 0, "0.5.2": 0, "0.5.3": 0, "0.5.4": 0,
                    "0.5.5": 0, "0.5.6": 0, "0.5.7": 0, "0.5.8": 0, "0.5.9": 0, "0.5.10": 0, "0.5.11": 0, "0.5.12": 0, "0.5.13": 0, "0.5.14": 0, "0.5.15": 0,
                    "0.5.16": 0, "0.5.17": 0, "0.6.0": 0, "0.6.1": 0, "0.6.2": 0, "0.6.3": 0, "0.6.4": 0, "0.6.5": 0, "0.6.6": 0, "0.6.7": 0, "0.6.8": 0, "0.6.9": 0,
                    "0.6.10": 0, "0.6.11": 0, "0.6.12": 0, "0.7.0": 0, "0.7.1": 0, "0.7.2": 0, "0.7.3": 0, "0.7.4": 0, "0.7.5": 0, "0.7.6": 0, "0.8.0": 0, "0.8.1": 0,
                    "0.8.2": 0, "0.8.3": 0, "0.8.4": 0, "0.8.5": 0, "0.8.6": 0, "0.8.7": 0, "0.8.8": 0, "0.8.9": 0, "0.8.10": 0, "0.8.11": 0, "0.8.12": 0, "0.8.13": 0,
                    "0.8.14": 0, "0.8.15": 0}
    # 遍历每一行pragma计算出来的结果，然后修改hash表
    for version_list in versions:
        for version in version_list:
            version_hash[version] += 1
    # 统计hash表中最符合的版本号是谁即可。
    for item in list(version_hash.keys())[::-1]:
        if version_hash[item] == len(versions):
            return item
