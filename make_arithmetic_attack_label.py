from queue import LifoQueue, Queue
from bean.Node import Node
import datetime
import config
import utils


# 对文件进行打溢出漏洞标签的操作。
# project_node_dict：节点的列表
# file_name:源文件的名字，抽象语法树的json文件。
def make_arithmetic_attack_label(project_node_dict, file_name):
    # 存储和每一个BinaryOperation类型节点最近的控制流节点的数组。
    binary_operation_control_node_list = []
    # 先判断是否含有BinaryOperation的键，只有键存在才能进行遍历操作。
    if "BinaryOperation" in project_node_dict.keys():
        for binary_operation_node in project_node_dict["BinaryOperation"]:
            # 获取所有BinaryOperation节点最接近的控制流节点。
            res = get_all_control_node_of_binary_operation(binary_operation_node)
            # 将所有的计算结果添加到binary_operation_control_node_list数组中，注意必须得是独一无二的。
            if res not in binary_operation_control_node_list:
                binary_operation_control_node_list.append(res)
    # 存储所有的require节点，以及该require节点中使用的判定表达式。
    require_node_and_condition_node_dict_list = []
    if "require" in project_node_dict.keys():
        for require_node in project_node_dict["require"]:
            # 先取出require节点下面使用的函数调用节点。
            function_call_node = require_node.childes[0]
            # 获取条件表达式的节点id和节点类型。
            condition_node_id = function_call_node.attribute["arguments"][0][0]["id"]
            condition_node_type = function_call_node.attribute["arguments"][0][0]["nodeType"]
            # 遍历require节点的所有子节点，找出对应的判定表达式节点。
            for condition_node in function_call_node.childes:
                if condition_node.node_id == condition_node_id and condition_node.node_type == condition_node_type:
                    # 将找到的require节点和使用的表达式节点，作为一个字典数组保存下来。
                    require_node_and_condition_node_dict_list.append({"require_node": require_node, "condition_node": condition_node})
    # 进入函数的时间
    enter_time = datetime.datetime.now()
    # 记录回溯的操作结果的
    has_arithmetic_flag = []
    # 如果是generate_all，并不需要继续操作，因为这时候在create_corpus_txt的时候已经生成过标签了。
    if config.create_corpus_mode == "generate_all":
        return
    # 默认没有溢出漏洞，只有当发现了溢出漏洞的时候，才会修改该标签，以确定返回值。
    arithmetic_flag = False
    # 遍历当前合约中的ContractDefinition节点，因为获取预定义参数的时候对于不同的ContractDefinition节点来说是不一样的。
    for contract_node in project_node_dict['ContractDefinition']:
        # 如果在某一次循环中已经发现当前文件中是带有漏洞的，直接退出循环
        if arithmetic_flag:
            break
        # 代表合约中预定义的参数，后面进行控制流回溯的时候会用到。
        pre_variable_node_list = []
        # 遍历ContractDefinition节点下面的子节点，这些子节点就是预定义参数的节点。
        for variable_declaration_node in contract_node.childes:
            # 当类型是VariableDeclaration的时候，才是参数预定义，注意，在这个位置不管有没有等号赋值都只会是VariableDeclaration。
            if variable_declaration_node.node_type == "VariableDeclaration":
                # 将当前这个变量的节点添加到数组中。
                pre_variable_node_list.append(variable_declaration_node)
        if "FunctionDefinition" in project_node_dict.keys():
            # 遍历合约当中的函数定义节点，对每一个函数分开来进行判断。
            for function_definition_node in project_node_dict["FunctionDefinition"]:
                # 必须是在当前的合约下面，而且当前的函数有内容，才能进行漏洞判断。
                if function_definition_node.parent == contract_node and len(function_definition_node.control_childes):
                    # 获取当前FunctionDefinition节点定义的入参和出参。
                    method_params, method_returns = get_method_message_at_function_definition_node(function_definition_node)
                    # 将预定义的参数和入参放到一起，送入到回溯的函数中进行操作。
                    for pre_variable in pre_variable_node_list:
                        method_params.append(pre_variable)
                    now_node = None
                    # 先找出第一个应该走的节点是谁，不能够直接使用control_childes[0]，容易弄到修饰符上去。
                    for control_child in function_definition_node.control_childes:
                        if control_child.node_type != "ModifierDefinition":
                            now_node = control_child
                            break
                    # 进行控制流+回溯的操作，判断在每一个控制流上是不是都是安全的。
                    traverse_arithmetic_attack(project_node_dict, function_definition_node, method_params, now_node, [], has_arithmetic_flag, enter_time, binary_operation_control_node_list, require_node_and_condition_node_dict_list)
                    if len(has_arithmetic_flag):
                        arithmetic_flag = True
                        break
    print(f"{file_name}溢出漏洞已经检测完毕。")
    # 最终返回这个控制的变量即可。
    if arithmetic_flag:
        return has_arithmetic_flag[0]
    else:
        return 0


# 返回所有的BinaryOperation节点的最近的控制流节点是谁。
# binary_operation_node：传入的BinaryOperation节点
def get_all_control_node_of_binary_operation(binary_operation_node):
    while len(binary_operation_node.control_childes) == 0:
        binary_operation_node = binary_operation_node.parent
        if binary_operation_node is None:
            return []
    return binary_operation_node


# 找到一个FunctionDefinition节点下面的入参和出参,返回值是两个数组
def get_method_message_at_function_definition_node(function_definition_node):
    # 保存当前这个FunctionDefinition节点下面的入参和出参使用的数组。
    method_params = []
    method_returns = []
    # 计数器，用来区分下面遍历到的ParameterList代表的是入参还是出参。
    flag = 0
    # 遍历函数定义节点的子节点，从中取出入参和出参。
    for child in function_definition_node.childes:
        if child.node_type == "ParameterList":
            # 修改计数器，改变当前的参数类型是入参还是出参。
            flag += 1
            # 遍历ParameterList的子节点，因为我要取的入参和出参是VariableDefinition节点，是他们的子节点，而不是ParameterList。
            for child_node_of_parameter_list in child.childes:
                # 每一个FunctionDefinition节点下面都会有两个ParameterList，一般来说第一个就是参数节点，第二个是返回值节点。
                if child_node_of_parameter_list.node_type == "VariableDeclaration" and flag == 1:
                    method_params.append(child_node_of_parameter_list)
                if child_node_of_parameter_list.node_type == "VariableDeclaration" and flag == 2:
                    method_returns.append(child_node_of_parameter_list)
    return method_params, method_returns


# 返回节点node，是不是functionDefinition节点的子节点，True代表是，False代表不是。
def is_child_of_function_definition_node(node, function_definition_node):
    # 先设定parent，然后不断的往上迭代,判断是不是合理的函数定义节点的效果范围内。
    parent = node
    while parent is not None:
        if parent is function_definition_node:
            return True
        else:
            parent = parent.parent
    return False


# 查出在当前位置的子树中，有多少个可以连接的节点。
def get_all_literal_or_identifier_at_now(node):
    res = []
    stack = LifoQueue(maxsize=0)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        for child in pop_node.childes:
            # 如果是block那就代表该停下来了，因为下面的内容不是当前行可以获取的。
            if child.node_type != "Block":
                stack.put(child)
        if pop_node.node_type in ["Literal", "Identifier", "MemberAccess", "IndexAccess", "VariableDeclaration"]:
            res.append(pop_node)
    return res


# 进行回溯+控制流遍历所有的控制流路线
# project_node_dict:暂时还没有用处，先放着。
# function_definition_node:函数定义节点，到时候可以判断是不是走到了另外的函数定义节点的域中。
# params:到当前位置的时候,已经被记录的参数
# now_node:当前的节点位置
# path:记录所有走过的节点,以避免进行死循环
# has_arithmetic_flag:用来记录结果的数组
# enter_time:开始运行的时间。
# binary_operation_control_node_list：每一个BinaryOperation节点的控制流节点的数组。
# require_node_and_condition_node_dict_list：每一个require以及他的判定节点。
def traverse_arithmetic_attack(project_node_dict, function_definition_node, params, now_node, path, has_arithmetic_flag, enter_time, binary_operation_control_node_list, require_node_and_condition_node_dict_list):
    # 此刻的时间
    now_time = datetime.datetime.now()
    # 打标签的时间太长了
    if (now_time - enter_time).seconds > config.make_arithmetic_attack_label_max_time:
        raise utils.CustomError("溢出漏洞标签耗时过久，已被移入error文件夹")
    # 如果当前节点不是属于当前的函数定义节点的子节点,结束当前路径。
    if is_child_of_function_definition_node(now_node, function_definition_node) is False:
        result = arithmetic_attack(params, path, binary_operation_control_node_list, require_node_and_condition_node_dict_list)
        # 当前这条路已经走到底了，判断这条路上是否含有算数溢出的漏洞。
        if result == 1 or result == 2:
            has_arithmetic_flag.append(result)
        return
    # 计数器：记录当前这个节点已经在路径中出现了几次，当出现了两次及以上的时候，说明陷入了死循环，直接退出。
    count = 0
    # 遍历所有的已经路过的节点，如果当前节点出现了，那就增加计数器
    for gone_node in path:
        if now_node == gone_node:
            count += 1
    # 如果这个节点已经走过两次了，那也结束当前路径，因为这代表进入了死循环之类的。
    if count >= 2:
        # 当前这条路已经走到底了，判断这条路上是否含有算数溢出的漏洞。
        result = arithmetic_attack(params, path, binary_operation_control_node_list, require_node_and_condition_node_dict_list)
        if result == 1 or result == 2:
            has_arithmetic_flag.append(result)
        return
    # 是否已经进行了回溯的标签
    has_traverse_flag = False
    # 进行回溯操作
    for control_child in now_node.control_childes:
        # 如果要走的节点是上一个刚过来的节点，那就跳过，适用于直接进入FunctionCall，并且马上退出的。
        # 总之就是遇见require不能直接停下来，会对后面的判断产生影响。
        if len(path) > 0 and control_child == path[-1] and control_child.node_type == "FunctionCall":
            continue
        # 已经找到漏洞了，不再进行深一步的循环
        if len(has_arithmetic_flag) != 0:
            continue
        path.append(now_node)
        has_traverse_flag = True
        # 进一步的进行检测
        traverse_arithmetic_attack(project_node_dict, function_definition_node, params, control_child, path, has_arithmetic_flag, enter_time, binary_operation_control_node_list, require_node_and_condition_node_dict_list)
        path.pop(-1)
    # 没有进行回溯的节点，说明已经走到头了，可以对当前这条完整的控制流进行判断。
    if has_traverse_flag is False:
        # 一定要像回溯一样，否则最后一个节点不会被记录下来。
        path.append(now_node)
        # 当前这条路已经走到底了，判断这条路上是否含有算数溢出的漏洞。
        result = arithmetic_attack(params, path, binary_operation_control_node_list, require_node_and_condition_node_dict_list)
        if result == 1 or result == 2:
            has_arithmetic_flag.append(result)
        path.pop(-1)
        return


# pre_variable_list：预定义的参数列表。
# path:回溯走过的路径。
# binary_operation_control_node_list：每一个BinaryOperation的节点对应的控制流节点。
# require_node_and_condition_node_dict_list：每一个require以及对应的判定符号的节点组成的字典数组。
# 如果存在漏洞，则返回True，否则返回False。
def arithmetic_attack(pre_variable_list, path, binary_operation_control_node_list, require_node_and_condition_node_dict_list):
    # 先获取当前路径上所有用过的参数以及require节点。
    params, require_list = path_simulation(path, pre_variable_list)
    # 从节点字典中进行查询，比遍历更快。
    for binary_operation_control_node in binary_operation_control_node_list:
        # 如果binaryOperation的控制流节点发现是在path中,说明可能出现了我们要寻找的目标，也就是溢出漏洞。注意require中的不算。
        if binary_operation_control_node in path and binary_operation_control_node.node_type != "FunctionCall":
            # 获取当前控制流节点下面每一个BinaryOperation的详细情况，每一个Binary会贡献一个对象。
            binary_operation_node_list = get_binary_operation_node_list_of_root(binary_operation_control_node)
            if len(binary_operation_node_list) > 1:
                return 2
            # 循环其中每一个BinaryOperation，判断我构造出的条件表达式和require中原始给定的条件表达式是否相同，如果不同，直接返回True，代表源文件中存在漏洞。
            for binary_operation_node in binary_operation_node_list:
                # 只要其中有一个BinaryOperation没有找到断言，那就直接返回True，代表存在漏洞。
                if has_same_construct(binary_operation_node["left_variable"], binary_operation_node["right_variable"], binary_operation_node["result_variable"], binary_operation_node["operator"], require_node_and_condition_node_dict_list, path, params, binary_operation_control_node) is False:
                    return 1
    # 经过上面的验证，所有都已经经过了验证，那就说明没有漏洞。
    return 0


# 模拟走一遍path，然后将所有的参数和原始的预定义参数列表加在一起，同时在遍历的过程中，找出所有的require节点。
# 返回参数列表和require节点列表。
def path_simulation(path, pre_variable_list):
    # 先读取原始的预定义参数。
    params = []
    for variable in pre_variable_list:
        params.append(variable)
    # 存放所有require节点的地方。
    require_list = []
    # 遍历路径上每一个节点。
    for node in path:
        # 这是当前节点下所有可以记录的参数列表
        all_could_connect_param = get_all_literal_or_identifier_at_now(node)
        # 将这些参数统统和预定义参数记录在一起。
        for param in all_could_connect_param:
            if param not in params:
                params.append(param)
        if node.node_type == "require":
            require_list.append(node)
    return params, require_list


# 取得一个节点下面所有的二元操作符,因为一棵树中可能会有多个BinaryOperation.
# 返回结果是一个数组，每一个元素是一个字典，其中有左变量，右边量，符号，结果，BinaryOperation根节点五种属性。
def get_binary_operation_node_list_of_root(root):
    binary_operation_list = []
    # 这里需要使用广度遍历，以使得获取的根节点列表是有先后顺序的
    queue = Queue(maxsize=0)
    queue.put(root)
    while not queue.empty():
        pop_node = queue.get()
        # 如果发现是操作符号的节点，记录下来。
        if pop_node.node_type == "BinaryOperation":
            # 注意一定要含有变量，而不能是两个常数。
            if has_variable(pop_node):
                # 如果祖先节点的类型是Assignment或者VariableDeclarationStatement，代表是等式。
                if parent_is_equal_node(pop_node) is not None:
                    obj = {"left_variable": pop_node.childes[0],
                           "right_variable": pop_node.childes[1],
                           "operator": pop_node.attribute["operator"][0],
                           "result_variable": pop_node.parent.childes[0],
                           "root": pop_node}
                # 代表不是等式，是直接使用比如说test(a + b),那就直接把整个式子当作结果。
                else:
                    obj = {"left_variable": pop_node.childes[0],
                           "right_variable": pop_node.childes[1],
                           "operator": pop_node.attribute["operator"][0],
                           "result_variable": pop_node,
                           "root": pop_node}
                binary_operation_list.append(obj)
        for child in pop_node.childes:
            queue.put(child)
    return binary_operation_list


# 判断一个节点下面是不是还有变量,返回true代表有，否则代表没有。
def has_variable(node):
    stack = LifoQueue(maxsize=0)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        for child in pop_node.childes:
            # 如果是block那就代表该停下来了，因为下面的内容不是当前行可以获取的。
            if child.node_type != "Block":
                stack.put(child)
        if pop_node.node_type in ["Identifier", "MemberAccess", "IndexAccess", "VariableDeclaration"]:
            return True
    return False


# 判断父节点是不是等式的代表节点，比如说等号和VariableDeclaration,遇见括号可以略过，其他节点停下。
# 如果找到了等式节点，那就返回等式节点，否则返回None
def parent_is_equal_node(node):
    tmp = node.parent
    while True:
        if tmp.node_type == "Assignment" or tmp.node_type == "VariableDeclarationStatement":
            return tmp
        elif tmp.node_type == "TupleExpression":
            tmp = tmp.parent
        else:
            return None


# 判断我构造的树和原始的树是否相同，原始的树来自于require中。
# left_variable:操作符号的左端子树
# right_variable:操作符号的右端子树
# result_variable：结果值。
# operator：操作符号。
# require_node_and_condition_node_dict_list:所有的require节点，同时还带有操作的节点
# path:整条路径，用来判断require_node是不是在路径中。
# params：这条路上所有的参数。
# binary_operation_control_node:每一个BinaryOperation节点的控制流节点组成的数组。
def has_same_construct(left_variable, right_variable, result_variable, operator, require_node_and_condition_node_dict_list, path, params, binary_operation_control_node):
    # 根据左右参数，结果值还有符号，构造树
    if operator == "+":
        # 操作符号
        result_variable_binary_operation_node_1 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_1.append_attribute("operator", ">=")
        result_variable_binary_operation_node_2 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_2.append_attribute("operator", "<=")
        # 复制两边的内容和结果值
        construct_left_variable = copy_node(left_variable)
        construct_right_variable = copy_node(right_variable)
        construct_result_variable = copy_node(result_variable)
        # 构造出四种可能的结果
        # 判断在所有的require节点中，含有和我构造的结构相同的判断。
        for require_node in require_node_and_condition_node_dict_list:
            # 下面是第一种和第二种，c >= a还有c >= b
            result_variable_binary_operation_node_1.append_child(construct_result_variable)
            result_variable_binary_operation_node_1.append_child(construct_left_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之后，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) < path.index(binary_operation_control_node):
                    continue
                # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                    return True
                else:
                    # 断开左变量，将右变量连上
                    result_variable_binary_operation_node_1.childes.pop(-1)
                    result_variable_binary_operation_node_1.append_child(construct_right_variable)
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                        return True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 下面是第三种和第四种，a <= c 和 b <= c
            result_variable_binary_operation_node_2.append_child(construct_left_variable)
            result_variable_binary_operation_node_2.append_child(construct_result_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之后，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) < path.index(binary_operation_control_node):
                    continue
                # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_2, params) is True:
                    return True
                else:
                    # 断开左变量和右变量
                    result_variable_binary_operation_node_2.childes.pop(-1)
                    result_variable_binary_operation_node_2.childes.pop(-1)
                    result_variable_binary_operation_node_2.append_child(construct_right_variable)
                    result_variable_binary_operation_node_2.append_child(construct_result_variable)
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_2, params) is True:
                        return True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_2.childes.pop(-1)
        # 遍历了每一个require节点，都发现没有符合当前的BinaryOperation的断言，那就直接返回False，代表存在漏洞。
        return False
    elif operator == "-":
        # 操作符号
        result_variable_binary_operation_node_1 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_1.append_attribute("operator", "<=")
        result_variable_binary_operation_node_2 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_2.append_attribute("operator", ">=")
        # 复制两边的内容
        construct_left_variable = copy_node(left_variable)
        construct_right_variable = copy_node(right_variable)
        # 构造出两种可能的结果
        # 判断在所有的require节点中，含有和我构造的结构相同的判断。
        for require_node in require_node_and_condition_node_dict_list:
            # 下面是第一种，b <= a
            result_variable_binary_operation_node_1.append_child(construct_right_variable)
            result_variable_binary_operation_node_1.append_child(construct_left_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) > path.index(binary_operation_control_node):
                    continue
                # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                    return True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 下面是第二种，a >= b
            result_variable_binary_operation_node_2.append_child(construct_left_variable)
            result_variable_binary_operation_node_2.append_child(construct_right_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) > path.index(binary_operation_control_node):
                    continue
                # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_2, params) is True:
                    return True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_2.childes.pop(-1)
        # 遍历了每一个require节点，都发现没有符合当前的BinaryOperation的断言，那就直接返回False，代表存在漏洞。
        return False
    elif operator == "*":
        # 操作符号
        result_variable_binary_operation_node_1 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_1.append_attribute("operator", "==")
        result_variable_binary_operation_node_2 = Node(None, "BinaryOperation", None)
        result_variable_binary_operation_node_2.append_attribute("operator", "/")
        # 复制两边的内容以及0和结果值。
        construct_left_variable = copy_node(left_variable)
        construct_zero_literal = Node(None, "Literal", None)
        construct_zero_literal.append_attribute("src_code", "0")
        construct_right_variable = copy_node(right_variable)
        construct_result_variable = copy_node(result_variable)
        # 构造出两种可能的结果
        # 判断在所有的require节点中，含有和我构造的结构相同的判断。
        # 前置和后置是否含有断言的标记。
        has_pre_flag_a = False
        has_pre_flag_b = False
        has_post_flag_a = False
        has_post_flag_b = False
        for require_node in require_node_and_condition_node_dict_list:
            # 下面是第一种，a == 0
            result_variable_binary_operation_node_1.append_child(construct_left_variable)
            result_variable_binary_operation_node_1.append_child(construct_zero_literal)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) < path.index(binary_operation_control_node):
                    # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                        has_pre_flag_a = True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 下面是第二种，b == 0
            result_variable_binary_operation_node_1.append_child(construct_right_variable)
            result_variable_binary_operation_node_1.append_child(construct_zero_literal)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) < path.index(binary_operation_control_node):
                    # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                        has_pre_flag_b = True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 下面是第三种，c / a == b
            result_variable_binary_operation_node_2.append_child(construct_result_variable)
            result_variable_binary_operation_node_2.append_child(construct_left_variable)
            result_variable_binary_operation_node_1.append_child(result_variable_binary_operation_node_2)
            result_variable_binary_operation_node_1.append_child(construct_right_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) > path.index(binary_operation_control_node):
                    # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                        has_post_flag_a = True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 下面是第四种，c / b == a
            result_variable_binary_operation_node_2.append_child(construct_result_variable)
            result_variable_binary_operation_node_2.append_child(construct_right_variable)
            result_variable_binary_operation_node_1.append_child(result_variable_binary_operation_node_2)
            result_variable_binary_operation_node_1.append_child(construct_left_variable)
            # 如果是在路径当前中的，才有可能是当前控制流的断言语句。
            if require_node["require_node"] in path:
                # 先判断该require的位置对不对，如果不是在当前的BinaryOperation之前，就不需要进行后续的判断。
                if path.index(require_node["require_node"]) > path.index(binary_operation_control_node):
                    # 然后传入原始的每一个require下面判定条件，以及我构造的内容，判断结构是否相同。
                    if structure_equal(require_node["condition_node"], result_variable_binary_operation_node_1, params) is True:
                        has_post_flag_b = True
            # 断开左右的节点，以准备下次使用
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_2.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            result_variable_binary_operation_node_1.childes.pop(-1)
            # 判定最终结果:
            if (has_pre_flag_a and has_post_flag_a) or (has_pre_flag_b and has_post_flag_b):
                return True
        # 遍历了每一个require节点，都发现没有符合当前的BinaryOperation的断言，那就直接返回False，代表存在漏洞。
        return False


# 复制节点,以及所有的子域内容，需要根据不同类型节点复制不同内容。
def copy_node(origin_node):
    # 复制原始节点
    tmp_node = create_node(origin_node)
    stack = Queue(maxsize=0)
    # 一次性压入两个节点，作为一组。
    stack.put(tmp_node)
    stack.put(origin_node)
    while not stack.empty():
        # 一次性弹出两个节点
        pop_construct_node = stack.get()
        pop_origin_node = stack.get()
        # 遍历原始节点的所有子节点
        for child in pop_origin_node.childes:
            # 如果是参数类型，不用去复制，直接跳过。
            if child.node_type in ["ElementaryTypeName", "ElementaryTypeNameExpression", "FunctionTypeName", "UserDefinedTypeName", "ArrayTypeName"]:
                continue
            # 根据这里的子节点，复制，并连接
            tmp_child_node = create_node(child)
            pop_construct_node.append_child(tmp_child_node)
            # 再一次的同时压入两个节点
            stack.put(tmp_child_node)
            stack.put(child)
    return tmp_node


# 根据原始节点，创建新节点
def create_node(origin_node):
    if origin_node.node_type == "Identifier":
        res = Node(None, "Identifier", None)
        res.append_attribute("src_code", origin_node.attribute["src_code"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "Literal":
        res = Node(None, "Literal", None)
        res.append_attribute("src_code", origin_node.attribute["src_code"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "TupleExpression":
        res = Node(None, "TupleExpression", None)
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "MemberAccess":
        res = Node(None, "MemberAccess", None)
        res.append_attribute("src_code", origin_node.attribute["src_code"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "IndexAccess":
        res = Node(None, "IndexAccess", None)
        res.append_attribute("src_code", origin_node.attribute["src_code"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "BinaryOperation":
        res = Node(None, "BinaryOperation", None)
        res.append_attribute("operator", origin_node.attribute["operator"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res
    elif origin_node.node_type == "VariableDeclaration":
        res = Node(None, "Identifier", None)
        res.append_attribute("src_code", origin_node.attribute["name"][0])
        # 设定数据的来源，这里是固定的，如果有VariableDeclaration，那一定是从这里发射。
        res.data_parents.append(origin_node)
        return res
    elif origin_node.node_type == "FunctionCall":
        res = Node(None, "FunctionCall", None)
        res.append_attribute("src_code", origin_node.attribute["src_code"][0])
        # 可以在后面判断结构相同的时候，顺带判断是否来源相同。
        for data_parent in origin_node.data_parents:
            res.data_parents.append(data_parent)
        return res


# 判断两个结构是否完全一致。
def structure_equal(node_1, node_2, params):
    res_1 = []
    stack = LifoQueue(maxsize=0)
    stack.put(node_1)
    while not stack.empty():
        pop_node_1 = stack.get()
        res_1.append(pop_node_1)
        # 首先要节点类型相同。
        for child in pop_node_1.childes:
            stack.put(child)
    res_2 = []
    stack = LifoQueue(maxsize=0)
    stack.put(node_2)
    while not stack.empty():
        pop_node_2 = stack.get()
        res_2.append(pop_node_2)
        # 首先要节点类型相同。
        for child in pop_node_2.childes:
            stack.put(child)
    # 先判断长度是否相同。
    if len(res_1) != len(res_2):
        return False
    # 长度相同的情况下，判断内容是否相同。
    for res in zip(res_1, res_2):
        if res[0].node_type != res[1].node_type:
            return False
        # 是这四种类型的时候，比对src_code。
        if res[0].node_type in ["Identifier", "Literal", "IndexAccess", "MemberAccess", "FunctionCall"]:
            # 先比对他们的源代码是否相同，如果源代码都不一样，那可以直接返回False了。
            if res[0].attribute["src_code"] != res[1].attribute["src_code"]:
                return False
            else:
                # 遍历其中一个节点的数据流父节点
                for data_parent_1 in res[0].data_parents:
                    # 如果该数据流父节点也是另外一个数据流的父节点，同时在参数中出现过，那就是没有问题的，否则返回False。
                    if (data_parent_1 in res[1].data_parents and data_parent_1 in params) is False:
                        return False
        elif res[0].node_type == "BinaryOperation":
            # 比对操作符号是否相同,如果符号不一样，可以直接返回False
            if res[0].attribute["operator"] != res[1].attribute["operator"]:
                return False
    # 到最后都没有发现不对劲，那就直接返回True
    return True
