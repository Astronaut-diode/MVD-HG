import utils
import os
import config
import json
import random
import re
import shutil


# path：目标文件所在的位置
def merge(path, project_node_list, project_node_dict):
    path = path.replace("AST_json", "sol_source").replace(".json", ".sol")
    # 随机选取插入的位置
    insert_position = random_choose_insert_line(path)
    # 获取当前文件使用哪个版本进行编译
    versions = get_file_version(path)[0]
    for ite in range(10):
        find_flag = False
        for version in versions:
            # 判断对应的版本库中是否存在已经创建好的代码片段
            if os.path.exists(f"{config.code_snippet_library_path}/{version}"):
                # 对应版本库中所有的代码片段，从中随机挑选出一个代码片段，然后用来融合。
                snippet_file_list = os.listdir(f"{config.code_snippet_library_path}/{version}")
                snippet_file_path = f"{config.code_snippet_library_path}/{version}/" + snippet_file_list[random.randint(0, len(snippet_file_list) - 1)]
                # 开始合并文件
                target_file_path, diff_line = merge_file(origin_file_path=path, snippet_file_path=snippet_file_path, insert_position=insert_position, project_node_list=project_node_list, project_node_dict=project_node_dict)
                # 看看这个文件使用这个版本的编译器是否可以编译通过，如果编译可以通过，那么说明生成的文件是合理的。
                # 使用对应版本的编译器编译目标文件
                cmd = config.compile_dir_path + "solc-" + version + " " + target_file_path + " --combined-json ast --allow-paths " + target_file_path + " --ast-compact-json"
                # 执行编译的命令，使用popen可以保证内容不会直接输出到控制台上，否则太多了。
                f = os.popen(cmd, 'r')
                compile_flag = True
                for line in f.readlines():
                    # 大概率说明是编译失败的
                    if line.__contains__("Error"):
                        compile_flag = False
                        break
                opcode = f.close()
                if compile_flag and opcode is None:
                    utils.tip(f"{version}适配的代码片段存在,马上退出循环")
                    # 读取原始的行级标签的漏洞，然后对每一行进行diff_line的偏移，以更新漏洞所在的信息。
                    change_label_info(diff_line, target_file_path, path, snippet_file_path)
                    # 说明是存在合理的插入方式的,下次还要插入的话就得换一个版本号了。
                    versions.remove(version)
                    find_flag = True
                    break
                else:
                    utils.error(f"{target_file_path}使用{version}版本的编译器编译失败了,将使用下一个编译器。同时删除这个版本的文件")
                    os.remove(target_file_path)
                    utils.is_blank_now_dir(target_file_path[0:target_file_path.rfind("/")])
                    continue
            else:
                utils.error(f"{version}适配的代码片段不存在")
        # 说明当前轮次没有找到合理的插入方式，那后面也不可能有了
        if not find_flag:
            break
    # 此时应该将所有的tmp_dir中的内容移到原始的目录当中去。
    for dir_name in os.listdir(f"{config.data_dir_path}/tmp_dir/"):
        shutil.move(f"{config.data_dir_path}/tmp_dir/{dir_name}", f"{config.data_sol_source_dir_path}/")


# 读取目标文件的行级标签，判断应该将新的内容插入到哪一行的位置上。
# path是原始生成的文件的所在的路径。
# attack_type是攻击的类型。
def random_choose_insert_line(path, attack_type=config.attack_type_name):
    # 读取漏洞文件的信息，判断在具体哪一行进行数据增强。
    read_file_handle = open(f"{config.data_dir_path}/solidifi_labels.json", 'r')
    json_contents = json.load(read_file_handle)
    # 用来构造抽取随机line的总list的原始数据来源
    vulnerable_lines = json_contents[path[path.rfind("/") + 1:]][attack_type]
    # 待会用来抽取随机行的总list
    random_vulnerable_lines = []
    # 重新排序一下
    vulnerable_lines = sorted(vulnerable_lines)
    tmp = []
    for line in vulnerable_lines[0:]:
        # 这是为了第一行的时候特殊处理的部分。
        if len(tmp) == 0:
            tmp.append(line)
        # 如果是连续性的就一直往里面加入
        if line == tmp[-1] + 1:
            tmp.append(line)
        # 说明断开了
        else:
            # 这种情况一般都是带有函数头和函数结尾的
            if len(tmp) > 2:
                for t in tmp[1: -2]:
                    random_vulnerable_lines.append(t)
            # 这就代表curated中的漏洞标签了。
            else:
                for t in tmp:
                    random_vulnerable_lines.append(t)
            # 每一次断开以后，tmp都要重新清零，并加入当前元素，以保持循环不变性
            tmp.clear()
            tmp.append(line)
    random_index = random.randint(0, len(random_vulnerable_lines) - 1)
    utils.tip(f"{path}应该插入在{random_vulnerable_lines[random_index]}行")
    return random_vulnerable_lines[random_index]


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
    # return get_max_version(versions)
    # 这里并不需要选用最大的版本，因为只要版本符号就加入到对应的片段代码库中
    return versions


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


# 合并文件origin_file_path以及snippet_file_path
def merge_file(origin_file_path, snippet_file_path, insert_position, project_node_list, project_node_dict):
    # 查询到插入行属于哪个函数以及哪个合约
    function_end_line = -1
    function_line, contract_line = get_function_and_contract_msg_from_line(project_node_list, insert_position, project_node_dict)
    # 将生成的文件先放到tmp_dir中，因为这样子可以避免修改sol_source文件夹中的内容，这段代码还在循环中，如果修改了不太合适。
    dir_path = origin_file_path[:origin_file_path.rfind("/")] + "/" + origin_file_path[origin_file_path.rfind("/") + 1:].replace(".sol", "") + snippet_file_path[snippet_file_path.rfind("/") + 1:]
    target_file_path = dir_path.replace("sol_source/", "tmp_dir/")
    target_file_path = target_file_path[:target_file_path.rfind("tmp_dir/") + 7] + target_file_path[target_file_path.rfind("/"):-4] + target_file_path[target_file_path.rfind("/"):-4] + ".sol"
    # 优先确保目标文件夹是存在的
    utils.dir_exists(target_file_path[:target_file_path.rfind("/")])
    # 记录原始文件和改变以后每一行对应的位置的偏移量，也就是记录当前行之前有多少行是代码片段带来的。
    diff_line = [0]
    # 生成的目标文件。
    with open(origin_file_path, 'r') as origin, open(snippet_file_path, 'r') as snippet, open(target_file_path, 'w') as target:
        origin_lines = origin.readlines()
        origin_index = 0
        snippet_lines = snippet.readlines()
        snippet_index = 0
        # 此刻的函数头在哪一行已经知道了，所以可以用左右花括号匹配的方法来找到右括号
        function_end_line = function_line - 1
        embrace_count = 0
        # 判断是否已经读入过了左括号
        already_flag = False
        while True:
            if origin_lines[function_end_line].__contains__("{"):
                already_flag = True
                embrace_count += 1
            if origin_lines[function_end_line].__contains__("}"):
                embrace_count -= 1
                already_flag = True
            if embrace_count == 0 and already_flag:
                # 弥补索引和行号之间的差别
                function_end_line += 1
                break
            function_end_line += 1
        # 先写入片段代码，一直写到出现了====================合约的开始符号====================\n为止
        while True:
            line = snippet_lines[snippet_index]
            snippet_index += 1
            if line != "====================合约的开始符号====================\n":
                target.write(line)
                # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
                diff_line[-1] += 1
            else:
                break
        # 读取原始文件的内容，直到目标的合约行
        while True:
            line = origin_lines[origin_index]
            origin_index += 1
            target.write(line)
            # 读取原始文件：又有新的一行原始代码加入了，他和上一行的偏移行是一致的。
            diff_line.append(diff_line[-1])
            # 如果到达了目标行，写入以后就直接退出循环。
            if origin_index == contract_line:
                break
        # 读取代码片段直到函数定义开始的部分
        while True:
            line = snippet_lines[snippet_index]
            snippet_index += 1
            if line != "====================函数的开始符号====================\n":
                target.write(line)
                # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
                diff_line[-1] += 1
            else:
                break
        # 读取原始文件的内容，直到目标的函数行
        while True:
            line = origin_lines[origin_index]
            origin_index += 1
            target.write(line)
            # 读取原始文件：又有新的一行原始代码加入了，他和上一行的偏移行是一致的。
            diff_line.append(diff_line[-1])
            # 如果到达了目标行，写入以后就直接退出循环。
            if origin_index == function_line:
                break
        # 先写入while(false) {
        target.write("while(false) {\n")
        # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
        diff_line[-1] += 1
        # 读取代码片段直到函数结束的部分
        while True:
            line = snippet_lines[snippet_index]
            snippet_index += 1
            if line != "====================函数的结束符号====================\n":
                target.write(line)
                # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
                diff_line[-1] += 1
            else:
                break
        # 写入while循环的结束符号 }
        target.write("}\n")
        # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
        diff_line[-1] += 1
        # 读取原始文件的内容，直到目标的函数结束行
        while True:
            line = origin_lines[origin_index]
            origin_index += 1
            target.write(line)
            # 读取原始文件：又有新的一行原始代码加入了，他和上一行的偏移行是一致的。
            diff_line.append(diff_line[-1])
            # 如果到达了目标行，写入以后就直接退出循环。
            if origin_index == function_end_line:
                break
        # 读取代码片段的部分，直到合约结束的部分
        while True:
            line = snippet_lines[snippet_index]
            snippet_index += 1
            if line != "====================合约的结束符号====================\n":
                target.write(line)
                # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
                diff_line[-1] += 1
            else:
                break
        # 读取剩余所有的原始文件内容
        while origin_index < len(origin_lines):
            line = origin_lines[origin_index]
            origin_index += 1
            target.write(line)
            # 读取原始文件：又有新的一行原始代码加入了，他和上一行的偏移行是一致的。
            diff_line.append(diff_line[-1])
        # 读取剩余所有的代码片段内容
        while snippet_index < len(snippet_lines):
            line = snippet_lines[snippet_index]
            snippet_index += 1
            target.write(line)
            # 读取代码片段：记录当前的原始代码的最后一行已经偏移了多少行。
            diff_line[-1] += 1
    # 在最后一行是不要的
    return target_file_path, diff_line


# 根据行号，查询到该行属于哪个合约。哪个函数
def get_function_and_contract_msg_from_line(project_node_list, line_number, project_node_dict):
    for node in project_node_list:
        if node.owner_line == line_number:
            contract_name = node.owner_contract
            function_name = node.owner_function
            function_line = -1
            contract_line = -1
            # 遍历所有的函数定义节点和合约定义节点，找出对应的开始和结束位置。
            for function_definition_node in project_node_dict["FunctionDefinition"]:
                if function_definition_node.node_type == "FunctionDefinition" and function_definition_node.attribute["name"][0] == function_name and function_definition_node.owner_contract == contract_name:
                    function_line = function_definition_node.owner_line
            for contract_definition_node in project_node_dict["ContractDefinition"]:
                if contract_definition_node.node_type == "ContractDefinition" and contract_definition_node.attribute["name"][0] == contract_name:
                    contract_line = contract_definition_node.owner_line
            return [function_line, contract_line]


# 根据diff_line更新行级标签。
# diff_line:偏差数组
# target_file_path:目标文件的全路径
# origin_file_path:原始文件的全路径
# snippet_file_path:代码片段文件保存在code_snippet_library里面的全路径
def change_label_info(diff_line, target_file_path, origin_file_path, snippet_file_path):
    # 生成两个文件的名字
    target_file_name = target_file_path[target_file_path.rfind("/") + 1:]
    origin_file_name = origin_file_path[origin_file_path.rfind("/") + 1:]
    # 读取行级别漏洞标签文件
    line_file_path = config.data_dir_path + "/solidifi_labels.json"
    # 只有行级别标签文件存在的时候才需要更改标签
    if os.path.exists(line_file_path):
        origin_line_file = open(line_file_path, 'r')
        origin_line_content = json.load(origin_line_file)
        # 根据原始行推演插入以后的目标行。
        res = []
        for vul_line in origin_line_content[origin_file_name][config.attack_type_name]:
            res.append(diff_line[vul_line - 1] + vul_line)
        origin_line_content[target_file_name] = {config.attack_type_name: res}
        origin_line_file.close()
        # 重新打开一个写入的句柄,并将修改以后的内容写入到文件当中去
        write_json = open(line_file_path, 'w')
        json.dump(origin_line_content, write_json)
        write_json.close()
    # 可视化对应行
    # succ = 0
    # for line, diff in enumerate(diff_line):
    #     if succ + 1 != line + diff + 1:
    #         utils.tip(f"\n{line + 1} {diff} => {line + 1 + diff}")
    #     else:
    #         utils.tip(f"{line + 1} {diff} => {line + 1 + diff}")
    #     succ = diff + line + 1
    # print()
    # 读取目标的代码片段包含了哪些合约信息
    snippet_code_contract_name_file = open(snippet_file_path.replace(".sol", ".json").replace("code_snippet_library", "code_snippet_json_library"), 'r')
    snippet_code_contract_name_json = json.load(snippet_code_contract_name_file)
    # 读取合约漏洞标签文件
    contract_file_path = config.data_dir_path + "/contract_labels.json"
    if os.path.exists(contract_file_path):
        origin_contract_file = open(contract_file_path, 'r')
        origin_contract_content = json.load(origin_contract_file)
        for contract in snippet_code_contract_name_json["contract_names"]:
            origin_contract_content.append({"contract_name": target_file_name.replace(".sol", "") + "-" + contract + ".sol", "targets": 0})
        origin_contract_file.close()
        # 改写内容
        update_contract_file_handle = open(contract_file_path, 'w')
        json.dump(origin_contract_content, update_contract_file_handle)
        update_contract_file_handle.close()
    snippet_code_contract_name_file.close()
