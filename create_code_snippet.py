import os
from queue import LifoQueue, Queue
import random
import config
import utils
import re
import shutil
import json


# project_node_list:整个异构图
# project_node_dict:将整个异构图中的节点进行了分类，制作成字典方便查询。
# snippet_file_name:生成的代码片段的文件的名字
# 根据当前文件抽象出来的异构图，挑出其中可以被直接摘出来的子图，然后作为一个片段保存为一份文件。
# =====================算法逻辑=====================
# 遍历整张图，找出其中可以被单独筛出来的部分，这一部分的特点是没有没有外部调用，也即没有控制流流向外部。
# 其次，这个文件会被分割为3个部分，一部分是全局的变量（包括处理逻辑用到的全局变量和传入给函数使用的参数，还有传出的部分），另外一部分是处理的逻辑，还有一部分应当是外链的部分。
# 每一部分的全局变量都会被插入到目标文件的全局域当中，另外处理的逻辑会被插在死代码中，然后放到漏洞代码的上一行去。
# 注意，目标函数的入参，实际上是局部变量，所以需要特殊处理一下。
# 版本号的处理，分为多个版本号文件夹，如果一个代码段可以用多种版本编译，那么就将其放入到多个文件夹当中。
# =====================算法逻辑=====================
def create_code_snippet(project_node_list, project_node_dict, snippet_file_name):
    snippet_file_name = snippet_file_name.replace("AST_json", "sol_source").replace(".json", ".sol")
    # 可以用来制作代码片段的函数定义节点，也就是出发点。
    normal_function_definition = find_all_function_definition_node_not_library(project_node_dict)
    # 创建指定数量的代码片段,但是有时侯可能函数定义节点的数量不足，所有取两者之间小的部分。
    for i in range(min(config.code_snippet_number, len(normal_function_definition))):
        # 先找出这个节点可以走的完整的控制流，把所有的节点按照顺序返回，而这个函数定义节点，是从刚刚的数组中随机选定的。
        random_function_id = random.randint(0, len(normal_function_definition) - 1)
        full_path = find_full_cfg_path_from_function_definition_node(normal_function_definition[random_function_id])
        # 根据这里找到的控制流全路径，找出所有使用到的ContractDefinition节点和FunctionDefinition节点
        function_definition_node_set, contract_definition_node_set = find_all_contract_and_function_definition_node_by_full_path(full_path, project_node_dict)
        # 根据继承类的关系，找出更多的相关类。
        contract_definition_node_set = find_all_base_contract(contract_definition_node_set, project_node_dict)
        # 求出所有目标函数和合约的名字，这样就不用遍历节点去寻找了。
        function_definition_node_name_set = set()
        for node in function_definition_node_set:
            function_definition_node_name_set.add(node.attribute["name"][0])
        contract_definition_node_name_set = set()
        for node in contract_definition_node_set:
            contract_definition_node_name_set.add(node.attribute["name"][0])
        # 找出控制流路线上每一个节点所涉及到的数据流节点，不论是数据流父节点还是数据流子节点
        involve_data_flow_node_set = find_all_data_flow_node_from_full_path(full_path, function_definition_node_name_set, contract_definition_node_name_set)
        # 至此，已经获得了数据流全部相关的节点，控制流全部相关的节点，所有涉及的contract以及函数的头节点。
        line_set = find_all_line_of_all_involve_node(full_path, function_definition_node_set, contract_definition_node_set, involve_data_flow_node_set)
        # 提前找出开始的函数所在的合约的节点对象。
        for node in contract_definition_node_set:
            # 如果遍历的合约的名字等于函数所在的合约
            if node.attribute["name"][0] == normal_function_definition[random_function_id].owner_contract:
                # 使用上面所述的行，去读写原始的合约文件，并裁剪出code_snippet,但是里面的右括号需要特殊处理一下。
                use_line_set_to_create_code_snippet(line_set, snippet_file_name, normal_function_definition[random_function_id], node, project_node_dict, contract_definition_node_set)
                break
        # 此时操作都已经完成了，需要避免下次继续随机到这个方法节点。
        normal_function_definition.remove(normal_function_definition[random_function_id])


# 找到所有有实现部分的函数源代码的函数定义节点。
def find_all_function_definition_node_not_library(project_node_dict):
    normal_function_definition = []
    # 遍历所有的函数定义节点，找出其中具有具体实现的函数
    if "FunctionDefinition" in project_node_dict.keys():
        for function_definition_node in project_node_dict["FunctionDefinition"]:
            if function_definition_node.attribute["src_code"][0].__contains__("{") and function_definition_node.attribute["src_code"][0].__contains__("}"):
                has_modifier_definition_flag = False
                for next_step in function_definition_node.control_childes:
                    if next_step.node_type == "ModifierDefinition":
                        has_modifier_definition_flag = True
                        break
                if function_definition_node.attribute["method_name"][0] == "constructor" or not function_definition_node.attribute["implemented"][0] or function_definition_node.owner_contract == "SafeMath" or len(function_definition_node.attribute["src_code"][0]) < 150 or function_definition_node.attribute["superFunction"][0] is not None:
                    continue
                # 如果含有实现的部分，而且还没有修饰符的部分，记录为可以制作为代码片段的部分。
                if not has_modifier_definition_flag:
                    normal_function_definition.append(function_definition_node)
    return normal_function_definition


# 从这个随机的函数定义节点出发，走出完整的控制流。
def find_full_cfg_path_from_function_definition_node(normal_function_definition):
    full_path = []
    queue = LifoQueue(maxsize=0)
    queue.put(normal_function_definition)
    # 使用栈进行深度优先遍历
    while not queue.empty():
        now_node = queue.get()
        # 如果这个节点还没有被访问过，那么访问,同时可以进行下一部分的访问。
        # 如果节点访问过了，那么就说明已经连回来了，没有必要继续压栈，否则可能造成死循环。
        if not full_path.__contains__(now_node):
            full_path.append(now_node)
            for next_step in now_node.control_childes:
                # 筛选条件1：如果当前节点是一个外部的函数节点，而函数节点又有被别的函数调用，那么就会加入别的函数调用节点。
                # 避免的方法：如果当前的节点已经是一个外部的函数节点，那么需要判断，下一个使用的函数调用节点是不是函数头
                # 如果是函数头这种节点，说明是需要再一次调用，否则就是目标节点调用了他，然后他连接了回去。
                if now_node != normal_function_definition and now_node.node_type == "FunctionDefinition" and next_step.node_type != "FunctionDefinition":
                    continue
                queue.put(next_step)
    # 返回完整的路径。
    return full_path


# 根据这里找到的控制流全路径，找出所有使用到的ContractDefinition节点和FunctionDefinition节点
def find_all_contract_and_function_definition_node_by_full_path(full_path, project_node_dict):
    function_definition_node_set = set()
    contract_definition_node_set = set()
    for control_path_node in full_path:
        # 目标节点的所属合约
        owner_function = control_path_node.owner_function
        # 遍历所有的函数定义节点，找到名字相同的部分，如果名字相同，那么就是该函数定义节点
        for function_definition_node in project_node_dict["FunctionDefinition"]:
            if function_definition_node.attribute["name"][0] == owner_function:
                function_definition_node_set.add(function_definition_node)
                break
        # 目标结点的所属合约
        owner_contract = control_path_node.owner_contract
        # 遍历所有的合约定义节点，找到名字相同的部分，如果名字相同，那么就是该合约定义节点
        for contract_definition_node in project_node_dict["ContractDefinition"]:
            if contract_definition_node.attribute["name"][0] == owner_contract:
                contract_definition_node_set.add(contract_definition_node)
                break
    return function_definition_node_set, contract_definition_node_set


# 根据继承类的关系，找出更多的父类。
def find_all_base_contract(contract_definition_node_set, project_node_dict):
    stack = LifoQueue(maxsize=0)
    for contract_definition_node in contract_definition_node_set:
        stack.put(contract_definition_node)
    while not stack.empty():
        node = stack.get()
        if len(node.attribute["baseContracts"][0]) != 0:
            for ite in node.attribute["baseContracts"][0]:
                name = ite["baseName"]["name"]
                for tmp in project_node_dict["ContractDefinition"]:
                    # 找到了对应的合约节点，加入到set中。
                    if tmp.attribute["name"][0] == name:
                        if not contract_definition_node_set.__contains__(tmp):
                            stack.put(tmp)
                        contract_definition_node_set.add(tmp)
    return contract_definition_node_set


# 找出控制流路线上每一个节点所涉及到的数据流节点，不论是数据流父节点还是数据流子节点
def find_all_data_flow_node_from_full_path(full_path, function_definition_node_name_set, contract_definition_node_name_set):
    involve_data_flow_node_set = set()
    for node in full_path:
        stack = LifoQueue(maxsize=0)
        memory = set()
        stack.put(node)
        memory.add(node)
        # 找出目标结点的所有相关的数据流节点
        while not stack.empty():
            ite_node = stack.get()
            for data_flow_child_node in ite_node.data_childes:
                if not memory.__contains__(data_flow_child_node):
                    # 如果目标节点在函数列表中，或者在合约列表中，但是不在函数体中都可以记录。
                    if data_flow_child_node.owner_function in function_definition_node_name_set or (data_flow_child_node.owner_function == "" and data_flow_child_node.owner_contract in contract_definition_node_name_set):
                        involve_data_flow_node_set.add(data_flow_child_node)
                        stack.put(data_flow_child_node)
                        memory.add(data_flow_child_node)
            for data_flow_parent_node in ite_node.data_parents:
                if not memory.__contains__(data_flow_parent_node):
                    # 如果目标节点在函数列表中，或者在合约列表中，但是不在函数体中都可以记录。
                    if data_flow_parent_node.owner_function in function_definition_node_name_set or (data_flow_parent_node.owner_function == "" and data_flow_parent_node.owner_contract in contract_definition_node_name_set):
                        involve_data_flow_node_set.add(data_flow_parent_node)
                        stack.put(data_flow_parent_node)
                        memory.add(data_flow_parent_node)
            for ast_child in ite_node.childes:
                if not memory.__contains__(ast_child):
                    # 如果目标节点在函数列表中，或者在合约列表中，但是不在函数体中都可以记录。
                    if ast_child.owner_function in function_definition_node_name_set or (ast_child.owner_function == "" and ast_child.owner_contract in contract_definition_node_name_set):
                        stack.put(ast_child)
                        memory.add(ast_child)
    return involve_data_flow_node_set


# 根据上面几个方法找出所有的相关节点，过滤出所有相关的行
# full_path:控制流走的全路径
# function_definition_node_set:所有函数定义节点形成的set
# contract_definition_node_set:所有合约定义节点形成的set
# involve_data_flow_node_set:所有涉及到的数据流形成的set
def find_all_line_of_all_involve_node(full_path, function_definition_node_set, contract_definition_node_set, involve_data_flow_node_set):
    line_set = set()
    for node in full_path:
        line_set.add(node.owner_line)
    for node in function_definition_node_set:
        line_set.add(node.owner_line)
    for node in contract_definition_node_set:
        line_set.add(node.owner_line)
    for node in involve_data_flow_node_set:
        line_set.add(node.owner_line)
    return line_set


# 使用上面所述的行，去读写原始的合约文件，并裁剪出code_snippet,但是里面的右括号需要特殊处理一下。
# line_set:所有涉及到的代码行
# snippet_file_name:源代码文件的文件名字
# code_snippet_start_function_node:该文件当中起点函数的节点
# code_snippet_start_contract_node:该文件当中起点合约的节点
# project_node_dict:所有节点按照节点类型分类的字典
# contract_definition_node_set：所有合约的片段代码中出现的相关类
def use_line_set_to_create_code_snippet(line_set, snippet_file_name, code_snippet_start_function_node, code_snippet_start_contract_node, project_node_dict, contract_definition_node_set):
    stack = LifoQueue(maxsize=0)
    # 读取原始文件，将行的set集合中加入右括号的部分
    with open(snippet_file_name, 'r') as origin_file:
        for count, line in enumerate(origin_file.readlines()):
            # 判断当前行是否是代表版本号码的一行。
            # 如果有匹配上的，那就需要取出其中的版本号，也就是说当前行是pragma solidity ^xxx等。
            if re.search(config.version_match_rule, line):
                line_set.add(count + 1)
            contain_left_embrace = False
            contain_right_embrace = False
            # 如果当前行是包含一个左括号的，那么是需要判断是否是被采用的左括号。
            if line.__contains__("{"):
                contain_left_embrace = True
            if line.__contains__("}"):
                contain_right_embrace = True
            # 说明该行代码是在目标当中，加入到目标文件中。否则直接写入空行。
            if count + 1 in line_set:
                # 如果当前行含有左括号的，那么压入真左括号
                if contain_left_embrace:
                    stack.put(True)
            else:
                if contain_left_embrace:
                    stack.put(False)
            # 如果是含有右括号，那么就需要判断，这个右括号是否需要被加入到snippet当中。
            if contain_left_embrace is False and contain_right_embrace is True:
                if stack.get():
                    line_set.add(count + 1)
    # 确保代码片段的文件夹是存在的
    utils.dir_exists(snippet_file_name[:snippet_file_name.rfind("/")].replace("sol_source", "code_snippet"))
    # 是从哪个函数开始的，用这个函数，给文件命名，方便后期查阅
    code_snippet_start_function_name = code_snippet_start_function_node.owner_contract + "_" + code_snippet_start_function_node.attribute["name"][0]
    # 生成的代码片段文件的全路径。
    code_snippet_file_path = snippet_file_name.replace("sol_source", "code_snippet").replace(".sol", f"_{code_snippet_start_function_name}.sol")
    # 读取原始文件，并创建写入的目标临时文件
    with open(snippet_file_name, 'r') as origin_file, open(code_snippet_file_path, 'w') as snippet_file:
        origin_lines = origin_file.readlines()
        # 这说明这种文件格式不正常，直接舍弃。
        if len(origin_lines) < 10:
            utils.error(f"{snippet_file_name}内容格式异常，提前结束")
            return
        for count, line in enumerate(origin_lines):
            # 说明该行代码是在目标当中，加入到目标文件中。否则直接写入空行。
            if count + 1 in line_set:
                snippet_file.write(line)
            else:
                snippet_file.write("\n")
    # 获取生成的代码片段的编译版本集合
    versions = get_file_version(code_snippet_file_path)
    if len(versions) > 0:
        versions = versions[0]
    else:
        # 无法生成，所以需要删除准备编译的代码片段文件
        utils.error(f"{code_snippet_file_path}没有合适的版本，无法编译，所以删除代码片段文件。")
        os.remove(code_snippet_file_path)
        return
    # 遍历每一种版本
    for version in versions:
        # 使用对应版本的编译器编译目标文件
        cmd = config.compile_dir_path + "solc-" + version + " " + code_snippet_file_path + " --combined-json ast --allow-paths " + code_snippet_file_path + " --ast-compact-json"
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
            utils.success(f"{code_snippet_file_path}一阶段编译成功,接下来操作函数返回。")
            # 根据生成的删减版的sol文件，生成真正的代码片段文件文件。
            # 删减版的函数开始行以及合约的名字
            code_snippet_start_function_line = code_snippet_start_function_node.owner_line
            code_snippet_start_function_name = code_snippet_start_function_node.attribute["name"][0]
            code_snippet_start_contract_line = code_snippet_start_contract_node.owner_line
            code_snippet_start_contract_name = code_snippet_start_contract_node.attribute["name"][0]
            # 找到该函数的return句子所在的行列表
            code_snippet_return_lines = find_code_snippet_return_line(project_node_dict, code_snippet_start_function_name, code_snippet_start_function_line, code_snippet_start_contract_name, code_snippet_file_path)
            for ite in code_snippet_return_lines.values():
                if ite is None:
                    utils.error(f"{code_snippet_file_path}返回的应该是函数，但是实际上这个函数代表了好多个返回值，极难转换，所以直接不编译了，删除这个文件。")
                    os.remove(code_snippet_file_path)
                    return
            # 将生成的目标代码片段文件转换成部分是直接可以用的代码，部分是需要插入的代码
            tmp_file = transform_code_snippet(code_snippet_file_path, code_snippet_start_function_line, code_snippet_start_function_name, code_snippet_start_contract_line, code_snippet_start_contract_name, code_snippet_return_lines)
            # 此时删除创建的目标文件以及转移transform之后的文件到/AST-GNN/code_snippet/版本号/中
            # 暂时不要删除，为了能够创建多个版本。
            # os.remove(code_snippet_file_path)
            # 判断版本库在不在，如果存在，往里面移动文件。
            utils.dir_exists(f"{config.code_snippet_library_path}/{version}")
            shutil.move(tmp_file, f"{config.code_snippet_library_path}/{version}/{tmp_file[tmp_file.rfind('/'):].replace('_tmp', '')}")
            # 保存当前的代码片段融入了几个合约，方便后面改写漏洞标签的记录文件。确保代码片段json文件夹是存在的
            utils.dir_exists(config.code_snippet_library_path.replace('code_snippet_library', 'code_snippet_json_library'))
            utils.dir_exists(f"{config.code_snippet_library_path.replace('code_snippet_library', 'code_snippet_json_library')}/{version}")
            contract_info_json = open(f"{config.code_snippet_library_path.replace('code_snippet_library', 'code_snippet_json_library')}/{version}/{tmp_file[tmp_file.rfind('/') + 1:].replace('_tmp', '').replace('.sol', '.json')}", 'w')
            res = []
            for contract_node in contract_definition_node_set:
                res.append(contract_node.attribute["name"][0])
            content = {"contract_names": res}
            json.dump(content, contract_info_json)
            contract_info_json.close()
        else:
            utils.error(f"{code_snippet_file_path}使用{version}版本的编译器编译失败了,将使用下一个编译器。")
    # 删除放置在code_snippet中的文件。
    utils.error(f"{code_snippet_file_path}所有版本的编译器都已经使用完毕，准备删除生成的中间文件")
    os.remove(code_snippet_file_path)


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


# 将生成的目标代码片段文件转换成部分是直接可以用的代码，部分是需要插入的代码
# code_snippet_file_path:要转换的目标文件
# code_snippet_start_function_line：函数的起始行
# code_snippet_start_function_name：函数的名字
# code_snippet_start_contract_line：合约的起始行
# code_snippet_start_contract_name：合约的名字
# code_snippet_return_lines: 每一行return应该转换为什么东西
# 本质上还是有点粗粒度的，没有考虑到一行中有多个右括号，或者和别的字符黏在一起的情况。
def transform_code_snippet(code_snippet_file_path, code_snippet_start_function_line, code_snippet_start_function_name, code_snippet_start_contract_line, code_snippet_start_contract_name, code_snippet_return_lines):
    # 读取转换前的文件并且开启一个临时文件用来写入新的内容。
    with open(code_snippet_file_path, 'r') as read_file, open(code_snippet_file_path.replace(".sol", "_tmp.sol"), 'w') as write_file:
        # 是否已经到了目标合约的位置
        start_contract_flag = False
        contract_stack = LifoQueue(maxsize=0)
        # 是否已经到了目标函数的位置
        start_function_flag = False
        function_stack = LifoQueue(maxsize=0)
        for count, line in enumerate(read_file.readlines()):
            # 注意，每一行正常来说至多写入一次，否则可能有异常，所以用continue跳过别的操作。
            # 到达了目标合约，写入一些特殊的字符
            if count + 1 == code_snippet_start_contract_line:
                write_file.write("====================合约的开始符号====================\n")
                start_contract_flag = True
                if line.__contains__("{"):
                    contract_stack.put("{")
                if line.__contains__("}"):
                    contract_stack.get()
                continue
            # 到达了目标函数，这时候应该把函数头替换为入参们，并开启函数部分的栈。
            if count + 1 == code_snippet_start_function_line:
                # 写入转换以后的部分。
                write_file.write("====================函数的开始符号====================\n")
                write_file.write(transform_function_head_to_parameters(line))
                start_function_flag = True
                if line.__contains__("{"):
                    function_stack.put("{")
                    contract_stack.put("{")
                if line.__contains__("}"):
                    function_stack.get()
                    contract_stack.get()
                # 如果恰好弄完了，那么函数也就被读取完毕了，直接关闭函数栈。
                if function_stack.empty():
                    start_function_flag = False
                    write_file.write("====================函数的结束符号====================\n")
                    continue
                continue
            # 说明函数栈已经被开启了,判断是否有读入符号
            if start_function_flag:
                if line.__contains__("{"):
                    function_stack.put("{")
                    contract_stack.put("{")
                if line.__contains__("}"):
                    function_stack.get()
                    contract_stack.get()
                # 如果恰好弄完了，那么函数也就被读取完毕了，直接关闭函数栈。
                if function_stack.empty():
                    start_function_flag = False
                    write_file.write("====================函数的结束符号====================\n")
                    continue
            # 说明合约栈已经被开启了，判断是否有读入符号
            if start_contract_flag:
                if line.__contains__("{"):
                    contract_stack.put("{")
                if line.__contains__("}"):
                    contract_stack.get()
                # 如果栈为空了，那就说明该合约已经读取完毕，关闭栈
                if contract_stack.empty():
                    start_contract_flag = False
                    write_file.write("====================合约的结束符号====================\n")
                    continue
            # 如果是指定的return行，写我给定的东西。
            if count + 1 in code_snippet_return_lines.keys():
                write_file.write(code_snippet_return_lines[count + 1])
                continue
            # 正常写入内容
            write_file.write(line)
    return code_snippet_file_path.replace(".sol", "_tmp.sol")


# 转换函数头为入参
def transform_function_head_to_parameters(function_head):
    pattern = re.compile(r".*?\(([\w|\d| |,]*)\)?")
    parameters = re.match(pattern, function_head).group(1) + ","
    if parameters == ",":
        return ""
    parameters = parameters.replace(",", ";\n")
    return parameters


# 转换返回值的类型并直接返回要输入的结果
def transform_ret_to_parameters(function_head, source_codes):
    pattern = re.compile(r".*?returns( )*\(([\w|\d| |,]*)\)?")
    res = re.match(pattern, function_head)
    if res is None:
        return ""
    parameters = res.group(2) + " "
    if parameters == "":
        return ""
    parameters = parameters.split(",")
    if len(parameters) != len(source_codes):
        utils.error("返回值的参数类型数量和返回内容数量对不上")
        return None
    else:
        res = ""
        for i in range(len(parameters)):
            res += f"{parameters[i][:parameters[i].find(' ')]} ret_value_{i} = {source_codes[i]};\n"
        return res


# 找到目标函数的所有return句子所在行,以及给定需要转换输入的内容。
# project_node_dict:节点分类以后的字典
# code_snippet_start_function_name：入口函数的名字
# code_snippet_start_function_line：入口函数在第几行
# code_snippet_start_contract_name：入口合约名字
# code_snippet_file_path：转换目标的文件位置
def find_code_snippet_return_line(project_node_dict, code_snippet_start_function_name, code_snippet_start_function_line, code_snippet_start_contract_name, code_snippet_file_path):
    # # 先读取出函数头
    # with open(code_snippet_file_path, 'r') as read_file:
    #     function_head = read_file.readlines()[code_snippet_start_function_line - 1]
    # code_snippet_return_lines = {}
    # if "Return" not in project_node_dict.keys():
    #     return {}
    # for ret_node in project_node_dict["Return"]:
    #     if ret_node.owner_function == code_snippet_start_function_name and ret_node.owner_contract == code_snippet_start_contract_name:
    #         source_code = ret_node.attribute["src_code"][0]
    #         # 删除return和结尾的分号
    #         source_code = source_code.replace("return", "").replace(";", "")
    #         # 使用逗号隔开来
    #         source_codes = source_code.split(",")
    #         # 保存的格式为{行数: 转换以后的返回内容}
    #         code_snippet_return_lines[ret_node.owner_line] = transform_ret_to_parameters(function_head, source_codes)
    # return code_snippet_return_lines
    # # 先读取出函数头
    with open(code_snippet_file_path, 'r') as read_file:
        function_head = read_file.readlines()[code_snippet_start_function_line - 1]
    code_snippet_return_lines = {}
    if "Return" not in project_node_dict.keys():
        return {}
    for ret_node in project_node_dict["Return"]:
        if ret_node.owner_contract == code_snippet_start_contract_name and ret_node.owner_function == code_snippet_start_function_name:
            source_codes = []
            queue = Queue(maxsize=0)
            for child in ret_node.childes:
                queue.put(child)
            while not queue.empty():
                child = queue.get()
                if child.node_type == "TupleExpression":
                    for c in child.childes:
                        queue.put(c)
                    continue
                source_codes.append(child.attribute["src_code"][0])
            code_snippet_return_lines[ret_node.owner_line] = transform_ret_to_parameters(function_head, source_codes)
    return code_snippet_return_lines
