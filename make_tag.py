from queue import LifoQueue
import config
import json
import os


# 为当前的文件打上是否含有漏洞的标签。
def make_tag(project_node_dict, file_name):
    # 如果是generate_all，可以不走这个函数了，因为一开始create_corpus_txt的时候已经走过了。
    if config.create_corpus_mode == "generate_all":
        return
    if reentry_attack(project_node_dict):
        reentry_flag = 1
    else:
        reentry_flag = 0
    if timestamp_attack(project_node_dict):
        timestamp_flag = 1
    else:
        timestamp_flag = 0
    if arithmetic_attack(project_node_dict):
        arithmetic_flag = 1
    else:
        arithmetic_flag = 0
    if dangerous_delegate_call_attack(project_node_dict):
        delegate_call_flag = 1
    else:
        delegate_call_flag = 0
    label = [reentry_flag, timestamp_flag, arithmetic_flag, delegate_call_flag]
    update_label_file(file_name, label)
    print(f"{file_name}标签已经打上了。")


# 通过目标节点的节点类型以及子节点,但是还需要判断属于哪种子节点，来找到目标节点,根据这两个条件，找到的节点，依然可能是多个，需要继续筛选，所以用list。
# 注意，如果用的是数据流，那节点类型就不用了，直接用默认的参数。
# type_flag:1代表是抽象语法树子节点，2代表是控制流子节点，3代表是数据流子节点
def get_node_by_child_and_node_type_of_target(project_node_dict, child, node_type, type_flag):
    res = []
    if type_flag == 1:
        # 从字典中取出对应于这种属性的所有节点进行遍历
        for node in project_node_dict[node_type]:
            # 对上述每一个节点遍历其抽象语法树子节点
            for child_of_node in node.childes:
                # 若发现子节点就是给定的抽象语法树子节点，说明找到目标了，直接返回。
                if child_of_node is child:
                    res.append(node)
    if type_flag == 2:
        # 从字典中取出对应于这种属性的所有节点进行遍历
        for node in project_node_dict[node_type]:
            # 对上述每一个节点遍历其控制流子节点
            for child_of_node in node.control_childes:
                # 若发现子节点就是给定的控制流子节点，说明找到目标了，直接返回。
                if child_of_node is child:
                    res.append(node)
    if type_flag == 3:
        # 从字典中取出对应于这种属性的所有节点进行遍历
        if "IndexAccess" in project_node_dict.keys():
            for node in project_node_dict["IndexAccess"]:
                # 对上述每一个节点遍历其数据流子节点
                for child_of_node in node.data_childes:
                    # 若发现子节点就是给定的数据流子节点，说明找到目标了，直接返回。
                    if child_of_node is child:
                        res.append(node)
        if "VariableDeclaration" in project_node_dict.keys():
            for node in project_node_dict["VariableDeclaration"]:
                # 对上述每一个节点遍历其数据流子节点
                for child_of_node in node.data_childes:
                    # 若发现子节点就是给定的数据流子节点，说明找到目标了，直接返回。
                    if child_of_node is child:
                        res.append(node)
        if "Identifier" in project_node_dict.keys():
            for node in project_node_dict["Identifier"]:
                # 对上述每一个节点遍历其数据流子节点
                for child_of_node in node.data_childes:
                    # 若发现子节点就是给定的数据流子节点，说明找到目标了，直接返回。
                    if child_of_node is child:
                        res.append(node)
    return res


# 获取当前节点的下游所有的数据流
def get_data_flow_downstream(node):
    res = []
    stack = LifoQueue(maxsize=0)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        # 如果已经走过了，需要退出。
        if pop_node in res:
            continue
        res.append(pop_node)
        for child_node in pop_node.data_childes:
            stack.put(child_node)
    return res


# 返回给定节点的子树列表中是否含有return或者transfer的函数,这里传入的节点一般是if或者三种循环的节点，所以在理论上来说，抽象语法树的子节点就是函数体。
def get_child_list_have_return_or_transfer(node):
    node_list = []
    stack = LifoQueue(maxsize=0)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        # 如果节点已经存在了，那就不需要做操作了，浪费算算力。
        if pop_node in node_list:
            continue
        # 如果发现含有Return当然需要返回。
        if pop_node.node_type == "Return":
            return True
        # 如果是FunctionCall，需要遇到以下的几种函数才能返回True
        if pop_node.node_type == "FunctionCall":
            # 装载参数列表的容器
            argument_list = []
            # 遍历参数的属性，获取所有的参数的id还有类型
            for argument in pop_node.attribute['arguments'][0]:
                argument_id = argument["id"]
                argument_node_type = argument["nodeType"]
                argument_list.append({"id": argument_id, "node_type": argument_node_type})
            # 遍历函数调用节点的所有的抽象语法树子节点
            for child in pop_node.childes:
                child_id = child.node_id
                child_node_type = child.node_type
                is_method = True
                # 如果发现当前的子节点在参数列表中出现过，那就说明当前的子节点是参数节点，不能用来判断函数是否是三种转账函数。
                for argument in argument_list:
                    argument_id = argument["id"]
                    argument_node_type = argument["node_type"]
                    if child_id == argument_id and child_node_type == argument_node_type:
                        is_method = False
                        break
                # 如果不是参数节点，而且是其中的某一种函数，说明是符合存在漏洞的模式的。
                if is_method and "src_code" in child.attribute.keys() and child.attribute["src_code"] in ["transfer", "send", "call.value"]:
                    return True
        # 将当前的节点记录为已经访问过，这样子下次就不会再次进入。
        node_list.append(pop_node)
        # 遍历所有的子节点，用来作为下一步。
        for child in pop_node.childes:
            stack.put(child)
    return False


# 判断当前节点是否在非require和assert的地方使用了,是的话返回True，否则返回False
def use_not_require_or_assert(node):
    while True:
        # 一直往上迭代，直到找到了require节点或者assert才能停止，否则就一直找到空为止。
        if node.node_type == "require" or node.node_type == "assert":
            return False
        node = node.parent
        if node is None:
            return True


# 更新标签文件
def update_label_file(file_name, label):
    # 先判断加工以后的json文件是否存在，如果不存在，先创建内容。
    if not os.path.exists(config.idx_to_label_file):
        write_json = open(config.idx_to_label_file, 'w')
        json.dump({}, write_json)
        write_json.close()
    # 这时候一定会有的，所以可以开始更新内容了。更新以后的保存内容应该是{"文件的名字": 标签, "文件的名字": 标签....}
    read_json = open(config.idx_to_label_file, 'r', encoding="utf-8")
    # 先读取原始的内容
    origin_content = json.load(read_json)
    # 对原始的内容进行更新
    origin_content.update({file_name: label})
    # 关闭读取的句柄
    read_json.close()
    # 重新打开一个写入的句柄
    write_json = open(config.idx_to_label_file, 'w')
    # 将更新以后的内容重新写入到json文件当中
    json.dump(origin_content, write_json)
    # 记得关闭比句柄文件。
    write_json.close()


# 判断当前的文件中是否含有重入攻击，如果有那么返回True，否则返回False。
def reentry_attack(project_node_dict):
    # 一个文件中只会含有一个WithdrawFunction用来代表外部合约中的Withdraw函数，如果有，说明当前的合约中含有call.value的部分，否则不会含有。
    if "WithdrawFunction" in project_node_dict.keys():
        withdraw_function_node = project_node_dict["WithdrawFunction"][0]
        # 找到对应的call.value语句，因为是他导致了withdraw节点。
        function_call_node = get_node_by_child_and_node_type_of_target(project_node_dict, withdraw_function_node, "FunctionCall", 2)
        # 这里取出来的结果是一个list，代表了整个文件中所有用到了call.value的地方，所以每一个call.value节点都需要遍历，如果其中含有重入攻击，可以直接返回True
        for tmp_node in function_call_node:
            # 去获取他使用的参数的详细信息
            argument_node_node_id = tmp_node.attribute["arguments"][0][0]["id"]
            argument_node_node_type = tmp_node.attribute["arguments"][0][0]["nodeType"]
            # 根据参数的详细信息取到对应的节点。
            for child_of_function_call_node in tmp_node.childes:
                # 找到了对应的参数节点。
                if child_of_function_call_node.node_id == argument_node_node_id and child_of_function_call_node.node_type == argument_node_node_type:
                    argument_node = child_of_function_call_node
                    if argument_node.attribute["src_code"] == "0":
                        return False
                    # 代码所处的位置，如果发现后面辐射的位置有比这个大的，那就说明是有重入的危险。
                    code_index = argument_node.attribute["src"][0].split(":")[0]
                    # 记录这个常数在之前是否使用过。
                    have_use_number_flag = False
                    # 代表是常数，那就直接去判断是否在后面使用过即可。
                    if argument_node.node_type == "Literal":
                        for node in project_node_dict["Literal"]:
                            # 说明这个常数在后面使用过。
                            if int(node.attribute["src"][0].split(":")[0]) > int(code_index):
                                return True
                            elif int(node.attribute["src"][0].split(":")[0]) < int(code_index):
                                have_use_number_flag = True
                        # 如果之前没有使用过，后面也没有使用过，那可以认为是白白转钱的操作，肯定有漏洞。
                        if not have_use_number_flag:
                            return True
                    # 代表和当前的这个参数等同效力的参数列表。
                    equal_list = []
                    if argument_node.node_type == "MemberAccess":
                        for member_access_node in project_node_dict["MemberAccess"]:
                            equal_list.append(member_access_node)
                    else:
                        equal_list.append(argument_node)
                    now_node = argument_node
                    while True:
                        # 根据当前节点，去寻找数据流的父节点是谁。
                        res = get_node_by_child_and_node_type_of_target(project_node_dict, now_node, None, 3)
                        # 如果找得到内容,就继续循环，否则直接退出，因为已经找到最前面了。
                        if res:
                            # 如果当前是IndexAccess，一般来说找到的结果会有两个，要清楚谁是主体。
                            if now_node.node_type == "IndexAccess":
                                # 找出主体部分的条件
                                base_expression_node_node_id = now_node.attribute["baseExpression"][0]["id"]
                                base_expression_node_node_type = now_node.attribute["baseExpression"][0]["nodeType"]
                                base_expression_node = None
                                # 然后根据抽象语法树子节点进行循环遍历。
                                for child in now_node.childes:
                                    if child.node_id == base_expression_node_node_id and child.node_type == base_expression_node_node_type:
                                        base_expression_node = child
                                # 将找到的结果添加到等价列表中。
                                equal_list.append(base_expression_node)
                                # 同时将这个结果作为下一个循环的节点。
                                now_node = base_expression_node
                            # 如果当前节点不是IndexAccess，那就简单的往上递推,这时候计算出来的结果肯定只有一个，所以如果计算出来的结果是IndexAccess，不需要管，如果是Identifier或者VariableDeclaration，记录为等效列表中。
                            else:
                                res_node = res[0]
                                if res_node.node_type == "IndexAccess":
                                    now_node = res_node
                                else:
                                    equal_list.append(res_node)
                                    now_node = res_node
                        else:
                            break
                    # 现在开始用这些等效参数，看看辐射影响了谁。
                    stack = LifoQueue(maxsize=0)
                    for equal_node in equal_list:
                        stack.put(equal_node)
                    # 记录哪些节点已经走过了，避免重复走。
                    already_dfs_list = []
                    # 开始对这些点进行深度遍历，查询数据流影响范围上有没有造成重入的部分。
                    while not stack.empty():
                        pop_node = stack.get()
                        # 已经遍历过的话直接跳过。
                        if pop_node in already_dfs_list:
                            continue
                        # 判断代码出现的位置是否大于原始call.value中参数出现的位置。
                        tmp_code_index = pop_node.attribute["src"][0].split(":")[0]
                        # 如果确定是大于的，那就直接返回True，否则记录当前节点已经被访问过了，而且要将所有的数据流子节点压入栈中，以进行下次循环。
                        if int(tmp_code_index) > int(code_index):
                            binary_operate_node = pop_node
                            while True:
                                # 判断是不是用了二元减号
                                if binary_operate_node.node_type == "BinaryOperation" and binary_operate_node.attribute["operator"][0] == "-":
                                    # 判断是不是在他的右变量中。
                                    if in_right_hand_side(binary_operate_node, pop_node):
                                        return True
                                elif binary_operate_node.node_type == "Assignment":
                                    # 判断pop_node是不是在他的右变量中。
                                    if binary_operate_node.attribute["operator"][0] == "-=" and in_right_hand_side(binary_operate_node, pop_node):
                                        return True
                                    #  如果是等号，必须要出现=0.
                                    elif binary_operate_node.attribute["operator"][0] == "=":
                                        if binary_operate_node.attribute["src_code"][0].replace(" ", "").__contains__("=0"):
                                            return True
                                binary_operate_node = binary_operate_node.parent
                                if binary_operate_node is None:
                                    break
                        else:
                            already_dfs_list.append(pop_node)
                            for child_of_pop_node in pop_node.data_childes:
                                # 注意，如果是FunctionCall节点记得要停下来，因为大概率调用函数以后的参数和当前其实没什么关系，或者说是一种映射关系，对当前的查询没有意义。
                                if child_of_pop_node.node_type != "FunctionCall":
                                    stack.put(child_of_pop_node)
    # 一直没有找到，当然是返回False了。
    return False


def timestamp_attack(project_node_dict):
    if "MemberAccess" in project_node_dict.keys():
        # 在所有的节点中先查询，是否存在timestamp的调用。
        for probability_node_of_timestamp in project_node_dict['MemberAccess']:
            code = probability_node_of_timestamp.attribute['src_code'][0]
            # 确实使用了block.timestamp，符合条件,进入循环,至此，第一个条件满足。
            if code == "block.timestamp":
                # 先查询是否进行了赋值，如果有赋值，需要记录同等效果的变量。
                # 一直往上进行递归，直到找到顶或者找到了VariableDeclarationStatement节点。
                recursion_node = probability_node_of_timestamp
                # 先判断当前当前的这个节点是不是用来赋值，进入while循环去判断。如果不是赋值语句，再去后面找是不是有直接使用的地方。
                while True:
                    # 1.找到了赋值的地方，这里代表的是完全创建新的变量，如uint a = 10;
                    # 2.这里是代表已经创建好的变量，新接受内容的情况,比如a = 10,a是一开始就创建好的。
                    if recursion_node.node_type == "VariableDeclarationStatement":
                        declarations_id = recursion_node.attribute['declarations'][0][0]['id']
                        declarations_node_type = recursion_node.attribute['declarations'][0][0]['nodeType']
                        for declarations_node in recursion_node.childes:
                            if declarations_node.node_id == declarations_id and declarations_node.node_type == declarations_node_type:
                                # 赋值的对象就是当前节点的数据流下一个节点
                                variable_node = declarations_node
                                # 然后通过判断这个赋值对象是否在后面被用过，就能判断出来有没有时间戳漏洞。
                                use_list = get_data_flow_downstream(variable_node)
                                # 根本不需要记录下标，因为能在后面出现的，肯定是已经在当前行下面了。
                                for use_node in use_list:
                                    # 如果发现其中的某一个节点不是在require或者assert中，那就说明有可能存在问题。
                                    if use_not_require_or_assert(use_node):
                                        return True
                    if recursion_node.node_type == "Assignment":
                        left_hand_side_id = recursion_node.attribute['leftHandSide'][0]['id']
                        left_hand_side_node_type = recursion_node.attribute['leftHandSide'][0]['nodeType']
                        for left_hand_side_node in recursion_node.childes:
                            if left_hand_side_node.node_id == left_hand_side_id and left_hand_side_node.node_type == left_hand_side_node_type:
                                # 赋值的对象就是该值，也就是赋值左边的部分。
                                variable_node = left_hand_side_node
                                # 然后通过判断这个赋值对象是否在后面被用过，就能判断出来有没有时间戳漏洞。
                                use_list = get_data_flow_downstream(variable_node)
                                # 根本不需要记录下标，因为能在后面出现的，肯定是已经在当前行下面了。
                                for use_node in use_list:
                                    # 如果发现其中的某一个节点不是在require或者assert中，那就说明有可能存在问题。
                                    if use_not_require_or_assert(use_node):
                                        return True
                    recursion_node = recursion_node.parent
                    # 如果一直到结束都发现是None，那就可以排除赋值语句的情况,除了赋值语句的情况，还有直接使用的情况需要去继续判断。
                    if recursion_node is None:
                        break
                # 判断是否有直接使用的情况
                recursion_node = probability_node_of_timestamp
                while True:
                    # 如果在这四类当中，判断是不是在条件语句上，如果是的话，再深入判断是不是会印象转账或者return流的。
                    if recursion_node.node_type in ["IfStatement", "WhileStatement", "DoWhileStatement", "ForStatement"]:
                        condition_id = recursion_node.attribute["condition"][0]["id"]
                        condition_node_type = recursion_node.attribute["condition"][0]["nodeType"]
                        condition_node = None
                        for child_of_condition_node in recursion_node.childes:
                            # 如果匹配上了，也就是找到了条件节点。
                            if child_of_condition_node.node_id == condition_id and condition_node_type == condition_node_type:
                                condition_node = child_of_condition_node
                                break
                        # 从这个条件结点开始，找出子树中是否含有之前匹配到的probability_node_of_timestamp节点，含有的话就是说明被作为了判定条件。
                        stack = LifoQueue(maxsize=0)
                        stack.put(condition_node)
                        while not stack.empty():
                            pop_node = stack.get()
                            # 如果弹出节点是目标节点，就说明找到了时间戳作为判定条件的手段。
                            if pop_node is probability_node_of_timestamp:
                                # 还需要判断在block中是否含有转账或者return的操作，如果有，就返回True，否则不操作，因为后面可能还有使用时间戳的条件语句。
                                if get_child_list_have_return_or_transfer(recursion_node):
                                    return True
                            else:
                                for child in pop_node.childes:
                                    stack.put(child)
                    # 如果是在Return上可以直接返回True了。
                    elif recursion_node.node_type == "Return":
                        return True
                    recursion_node = recursion_node.parent
                    if recursion_node is None:
                        break
    # 下面是用来判断now的。
    if "Identifier" in project_node_dict.keys():
        # 在所有的节点中先查询，是否存在timestamp的调用。
        for probability_node_of_timestamp in project_node_dict['Identifier']:
            code = probability_node_of_timestamp.attribute['src_code'][0]
            # 确实使用了block.timestamp，符合条件,进入循环,至此，第一个条件满足。
            if code == "now":
                # 先查询是否进行了赋值，如果有赋值，需要记录同等效果的变量。
                # 一直往上进行递归，直到找到顶或者找到了VariableDeclarationStatement节点。
                recursion_node = probability_node_of_timestamp
                # 先判断当前当前的这个节点是不是用来赋值，进入while循环去判断。如果不是赋值语句，再去后面找是不是有直接使用的地方。
                while True:
                    if recursion_node.node_type == "VariableDeclarationStatement":
                        declarations_id = recursion_node.attribute['declarations'][0][0]['id']
                        declarations_node_type = recursion_node.attribute['declarations'][0][0]['nodeType']
                        for declarations_node in recursion_node.childes:
                            if declarations_node.node_id == declarations_id and declarations_node.node_type == declarations_node_type:
                                # 赋值的对象就是当前节点的数据流下一个节点
                                variable_node = declarations_node
                                # 然后通过判断这个赋值对象是否在后面被用过，就能判断出来有没有时间戳漏洞。
                                use_list = get_data_flow_downstream(variable_node)
                                # 根本不需要记录下标，因为能在后面出现的，肯定是已经在当前行下面了。
                                for use_node in use_list:
                                    # 如果发现其中的某一个节点不是在require或者assert中，那就说明有可能存在问题。
                                    if use_not_require_or_assert(use_node):
                                        return True
                    if recursion_node.node_type == "Assignment":
                        left_hand_side_id = recursion_node.attribute['leftHandSide'][0]['id']
                        left_hand_side_node_type = recursion_node.attribute['leftHandSide'][0]['nodeType']
                        for left_hand_side_node in recursion_node.childes:
                            if left_hand_side_node.node_id == left_hand_side_id and left_hand_side_node.node_type == left_hand_side_node_type:
                                # 赋值的对象就是该值，也就是赋值左边的部分。
                                variable_node = left_hand_side_node
                                # 然后通过判断这个赋值对象是否在后面被用过，就能判断出来有没有时间戳漏洞。
                                use_list = get_data_flow_downstream(variable_node)
                                # 根本不需要记录下标，因为能在后面出现的，肯定是已经在当前行下面了。
                                for use_node in use_list:
                                    # 如果发现其中的某一个节点不是在require或者assert中，那就说明有可能存在问题。
                                    if use_not_require_or_assert(use_node):
                                        return True
                    recursion_node = recursion_node.parent
                    # 如果一直到结束都发现是None，那就可以排除赋值语句的情况,除了赋值语句的情况，还有直接使用的情况需要去继续判断。
                    if recursion_node is None:
                        break
                # 判断是否有直接使用的情况
                recursion_node = probability_node_of_timestamp
                while True:
                    # 如果在这四类当中，判断是不是在条件语句上，如果是的话，再深入判断是不是会印象转账或者return流的。
                    if recursion_node.node_type in ["IfStatement", "WhileStatement", "DoWhileStatement", "ForStatement"]:
                        condition_id = recursion_node.attribute["condition"][0]["id"]
                        condition_node_type = recursion_node.attribute["condition"][0]["nodeType"]
                        condition_node = None
                        for child_of_condition_node in recursion_node.childes:
                            # 如果匹配上了，也就是找到了条件节点。
                            if child_of_condition_node.node_id == condition_id and condition_node_type == condition_node_type:
                                condition_node = child_of_condition_node
                                break
                        # 从这个条件结点开始，找出子树中是否含有之前匹配到的probability_node_of_timestamp节点，含有的话就是说明被作为了判定条件。
                        stack = LifoQueue(maxsize=0)
                        stack.put(condition_node)
                        while not stack.empty():
                            pop_node = stack.get()
                            # 如果弹出节点是目标节点，就说明找到了时间戳作为判定条件的手段。
                            if pop_node is probability_node_of_timestamp:
                                # 还需要判断在block中是否含有转账或者return的操作，如果有，就返回True，否则不操作，因为后面可能还有使用时间戳的条件语句。
                                if get_child_list_have_return_or_transfer(recursion_node):
                                    return True
                            else:
                                for child in pop_node.childes:
                                    stack.put(child)
                    # 如果是在Return上可以直接返回True了。
                    elif recursion_node.node_type == "Return":
                        return True
                    recursion_node = recursion_node.parent
                    if recursion_node is None:
                        break
    # 遍历完所有的节点，都没有发现可能还有时间戳漏洞的模式。
    return False


def in_right_hand_side(binary_operate_node, target_node):
    if "rightHandSide" in binary_operate_node.attribute.keys():
        right_hand_side_node_id = binary_operate_node.attribute["rightHandSide"][0]["id"]
        right_hand_side_node_type = binary_operate_node.attribute["rightHandSide"][0]["nodeType"]
    else:
        right_hand_side_node_id = binary_operate_node.attribute["rightExpression"][0]["id"]
        right_hand_side_node_type = binary_operate_node.attribute["rightExpression"][0]["nodeType"]
    for child in binary_operate_node.childes:
        if child.node_id == right_hand_side_node_id and child.node_type == right_hand_side_node_type:
            right_hand_side_node = child
            stack = LifoQueue(maxsize=0)
            stack.put(right_hand_side_node)
            while not stack.empty():
                pop_node = stack.get()
                if pop_node == target_node:
                    return True
                for tmp_child in pop_node.childes:
                    stack.put(tmp_child)
    return False


def dangerous_delegate_call_attack(project_node_dict):
    if "FunctionCall" in project_node_dict.keys():
        for function_call_node in project_node_dict["FunctionCall"]:
            # 如果这个键都不存在，直接跳过。
            if "memberName" not in function_call_node.attribute["expression"][0].keys():
                continue
            # 获取调用的函数的名字
            member_name = function_call_node.attribute["expression"][0]["memberName"]
            # 如果是delegatecall，满足了第一个条件。
            if member_name == "delegatecall":
                # 获取函数的调用者。
                for child in function_call_node.childes:
                    # 如果节点的值是符合条件的，那就说明这个节点是调用者，需要找到这个调用者的来源。
                    if child.attribute["memberName"][0] == "delegatecall":
                        # 找出所有的上级数据流节点
                        origin_list = []
                        stack = LifoQueue(maxsize=0)
                        stack.put(child)
                        while not stack.empty():
                            pop_node = stack.get()
                            if pop_node in origin_list:
                                continue
                            res = get_node_by_child_and_node_type_of_target(project_node_dict, pop_node, None, 3)
                            for origin_node in res:
                                stack.put(origin_node)
                                origin_list.append(origin_node)
                        for node in origin_list:
                            if node.parent.node_type == "ParameterList":
                                return True


def arithmetic_attack(project_node_dict):
    # 仅仅出现加减乘除
    if "BinaryOperation" in project_node_dict.keys():
        for binary_operation_node in project_node_dict["BinaryOperation"]:
            # 取出操作符号
            operator = binary_operation_node.attribute["operator"][0]
            if operator == "+":
                # 先取出加号的两端的内容,保存在res[0]和res[1]中，是数组形式，方便含有多个元素的时候进行操作。
                operation_obj_list = get_the_action_list_by_operation_node(binary_operation_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取赋值的对象以及控制流的节点
                    assignment_node_list, control_node = gets_the_assignment_object_and_the_control_flow_node(binary_operation_node)
                    # 如果上述的两个节点都不是None，那就说明可以直接判定为赋值操作。
                    if len(assignment_node_list) != 0 and control_node is not None:
                        # 注意，这里的时候是control_node当作控制流节点，不是赋值操作的话会将BinaryOperationNode当作控制流节点。
                        if the_value_has_been_updated_without_an_assertion_add(operation_obj_list, assignment_node_list, control_node):
                            return True
                    # 不是赋值操作。
                    else:
                        # 获取操作符号两边使用的所有的变量，添加到目标中。
                        assignment_node_list = []
                        # 将左右的所有参数添加到赋值目标中。
                        for operation_list in operation_obj_list:
                            for operation_obj in operation_list:
                                assignment_node_list.append(operation_obj)
                        tmp_node = binary_operation_node
                        while len(tmp_node.control_childes) == 0:
                            tmp_node = tmp_node.parent
                        control_node = tmp_node
                        if the_value_has_been_updated_without_an_assertion_add(operation_obj_list, assignment_node_list, control_node):
                            return True
            elif operator == "-":
                # 先取出减号的两端的内容,保存在res[0]和res[1]中，是数组形式，方便含有多个元素的时候进行操作。
                operation_obj_list = get_the_action_list_by_operation_node(binary_operation_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取赋值的对象以及控制流的节点
                    assignment_node_list, control_node = gets_the_assignment_object_and_the_control_flow_node(binary_operation_node)
                    # 如果上述的两个节点都不是None，那就说明可以直接判定为赋值操作。
                    if len(assignment_node_list) != 0 and control_node is not None:
                        # 减法的判断方式。
                        if the_value_has_been_updated_without_an_assertion_sub(operation_obj_list, control_node):
                            return True
                    # 不是赋值操作
                    else:
                        # 找出控制流节点，因为参数列表不需要变化，所以只要修改控制流节点即可实现不是赋值的时候的操作。
                        tmp_node = binary_operation_node
                        while len(tmp_node.control_childes) == 0:
                            tmp_node = tmp_node.parent
                        control_node = tmp_node
                        if the_value_has_been_updated_without_an_assertion_sub(operation_obj_list, control_node):
                            return True
            elif operator == "*":
                # 先取出乘号的两端的内容,保存在res[0]和res[1]中，是数组形式，方便含有多个元素的时候进行操作。
                operation_obj_list = get_the_action_list_by_operation_node(binary_operation_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取赋值的对象以及控制流的节点
                    assignment_node_list, control_node = gets_the_assignment_object_and_the_control_flow_node(binary_operation_node)
                    # 如果上述的两个节点都不是None，那就说明可以直接判定为赋值操作。
                    if len(assignment_node_list) > 0 and control_node is not None:
                        # 乘法的判断方式。
                        if the_value_has_been_updated_without_an_assertion_mul(operation_obj_list, assignment_node_list, control_node):
                            return True
                    # 不是赋值操作。
                    else:
                        # 获取操作符号两边使用的所有的变量，添加到目标中。
                        assignment_node_list = []
                        # 将左右的所有参数添加到赋值目标中。
                        for operation_list in operation_obj_list:
                            for operation_obj in operation_list:
                                assignment_node_list.append(operation_obj)
                        tmp_node = binary_operation_node
                        while len(tmp_node.control_childes) == 0:
                            tmp_node = tmp_node.parent
                        control_node = tmp_node
                        if the_value_has_been_updated_without_an_assertion_mul(operation_obj_list, assignment_node_list, control_node):
                            return True
    if "Assignment" in project_node_dict.keys():  # 这里有一个好处，不需要处理没有用在赋值情况下的条件，也就是不会用在函数的参数中，或者判断条件中。
        for assignment_node in project_node_dict["Assignment"]:
            operator = assignment_node.attribute["operator"][0]
            if operator == "+=":
                # 取出一端的内容，保存在数组中,原始的方法返回值一致
                operation_obj_list, assignment_node_list = get_the_action_list_by_assignment_node(assignment_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取控制流的节点
                    control_node = assignment_node.parent
                    # 因为是使用了Assignment，所以一定是赋值语句。
                    if the_value_has_been_updated_without_an_assertion_add(operation_obj_list, assignment_node_list, control_node):
                        return True
            elif operator == "-=":
                # 取出一端的内容，保存在数组中,原始的方法返回值一致
                operation_obj_list, assignment_node_list = get_the_action_list_by_assignment_node(assignment_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取控制流的节点
                    control_node = assignment_node.parent
                    # 因为是使用了Assignment，所以一定是赋值语句。
                    if the_value_has_been_updated_without_an_assertion_sub(operation_obj_list, control_node):
                        return True
            elif operator == "*=":
                # 取出一端的内容，保存在数组中,原始的方法返回值一致
                operation_obj_list, assignment_node_list = get_the_action_list_by_assignment_node(assignment_node)
                # 如果两个操作列表中，有一个是含有变量的，那就说明是可能含有溢出漏洞的，所以需要进一步处理。
                if has_variable(operation_obj_list[0]) or has_variable(operation_obj_list[1]):
                    # 根据操作符获取控制流的节点
                    control_node = assignment_node.parent
                    # 因为是使用了Assignment，所以一定是赋值语句。
                    if the_value_has_been_updated_without_an_assertion_mul(operation_obj_list, assignment_node_list, control_node):
                        return True


# 获取操作符号的所有参与计算的子节点，包含Identifier，Literal，MemberAccess
def get_the_action_list_by_operation_node(binary_operation_node):
    # 先获取左边的子节点。
    left_expression_node_id = binary_operation_node.attribute["leftExpression"][0]["id"]
    left_expression_node_type = binary_operation_node.attribute["leftExpression"][0]["nodeType"]
    left_expression_node_list = []
    right_expression_node_id = binary_operation_node.attribute["rightExpression"][0]["id"]
    right_expression_node_type = binary_operation_node.attribute["rightExpression"][0]["nodeType"]
    right_expression_node_list = []
    for child in binary_operation_node.childes:
        # 如果找到了左边的节点，遍历整个树，获取其中所有的变量。
        if child.node_id == left_expression_node_id and child.node_type == left_expression_node_type:
            stack = LifoQueue()
            stack.put(child)
            while not stack.empty():
                pop_node = stack.get()
                # 如果是这几种类型的节点，记录下来。
                if pop_node.node_type == "Identifier" or pop_node.node_type == "Literal" or pop_node.node_type == "MemberAccess":
                    left_expression_node_list.append(pop_node)
                # 将这里的子节点压入栈中继续遍历。
                for child_of_pop_node in pop_node.childes:
                    stack.put(child_of_pop_node)
        if child.node_id == right_expression_node_id and child.node_type == right_expression_node_type:
            stack = LifoQueue()
            stack.put(child)
            while not stack.empty():
                pop_node = stack.get()
                # 如果是这几种类型的节点，记录下来。
                if pop_node.node_type == "Identifier" or pop_node.node_type == "Literal" or pop_node.node_type == "MemberAccess":
                    right_expression_node_list.append(pop_node)
                # 将这里的子节点压入栈中继续遍历。
                for child_of_pop_node in pop_node.childes:
                    stack.put(child_of_pop_node)
    return [left_expression_node_list, right_expression_node_list]


# 获取操作符号的所有参与计算的子节点，包含Identifier，Literal，MemberAccess
def get_the_action_list_by_assignment_node(assignment_node):
    left_hand_side_node_id = assignment_node.attribute["leftHandSide"][0]["id"]
    left_hand_side_node_type = assignment_node.attribute["leftHandSide"][0]["nodeType"]
    left_hand_side_node_list = []
    right_hand_side_node_id = assignment_node.attribute["rightHandSide"][0]["id"]
    right_hand_side_node_type = assignment_node.attribute["rightHandSide"][0]["nodeType"]
    right_hand_side_node_list = []
    for child in assignment_node.childes:
        if child.node_id == left_hand_side_node_id and child.node_type == left_hand_side_node_type:
            stack = LifoQueue()
            stack.put(child)
            while not stack.empty():
                pop_node = stack.get()
                # 如果是这几种类型的节点，记录下来。
                if pop_node.node_type == "Identifier" or pop_node.node_type == "Literal" or pop_node.node_type == "MemberAccess":
                    left_hand_side_node_list.append(pop_node)
                # 将这里的子节点压入栈中继续遍历。
                for child_of_pop_node in pop_node.childes:
                    stack.put(child_of_pop_node)
        if child.node_id == right_hand_side_node_id and child.node_type == right_hand_side_node_type:
            stack = LifoQueue()
            stack.put(child)
            while not stack.empty():
                pop_node = stack.get()
                # 如果是这几种类型的节点，记录下来。
                if pop_node.node_type == "Identifier" or pop_node.node_type == "Literal" or pop_node.node_type == "MemberAccess":
                    right_hand_side_node_list.append(pop_node)
                # 将这里的子节点压入栈中继续遍历。
                for child_of_pop_node in pop_node.childes:
                    stack.put(child_of_pop_node)
    # 返回的内容是[右边的参数, 结果变量的列表]，[结果的变量]
    return [right_hand_side_node_list, left_hand_side_node_list], left_hand_side_node_list


# 判断一个res中是否含有变量，如果含有变量，返回True。
def has_variable(variable_list):
    for variable in variable_list:
        if variable.node_type != "Literal":
            return True
    return False


# 判断是不是用于赋值语句,如果是赋值语句，返回用来赋值的对象的节点和上级的控制流子节点。
def gets_the_assignment_object_and_the_control_flow_node(binary_operation_node):
    parent = binary_operation_node.parent
    if parent.node_type == "VariableDeclarationStatement":
        # 循环遍历其中的每一个子节点
        for child in parent.childes:
            # 如果子节点不是二元操作符，那就是我们的目标，也就是赋值点。
            if child is not binary_operation_node:
                return [child], parent
    elif parent.node_type == "Assignment":
        for child in parent.childes:
            if child is not binary_operation_node:
                return [child], parent
    else:
        return [], None


# 根据目标的控制流节点，去判断在每一条控制流的路上，是否都存在断言语句，如果是那就返回False，一旦发现不存在断言，就返回True。
def the_value_has_been_updated_without_an_assertion_add(operation_obj_list, assignment_node_list, control_node):
    pass_flag_count = 0
    # 开始遍历控制流,这里使用遍历是因为为了避免有分岔路。
    for start_control_path in control_node.control_childes:
        # 每一条控制流路线上的标记都得刷新,代表在断言之前是否被更新过。
        the_left_argument_updates_the_flag = False
        the_right_argument_updates_the_flag = False
        the_target_updates_the_flag = False
        # 判断左边的参数是不是有未出现的，一开始是False，如果查到了有，那就是True。
        the_left_parameter_has_unused_content = False
        the_right_parameter_has_unused_content = False
        the_target_has_unused_content = False
        # 一条控制流路线上的是否有符合条件的require已经被找到了。
        pass_flag = False
        # 对这条路进行深度遍历，找出其中不合理的位置。
        stack = LifoQueue(maxsize=0)
        stack.put(start_control_path)
        route_already_taken = []
        while not stack.empty():
            pop_node = stack.get()
            # 如果是FunctionCall节点是禁止的路线，因为这个方向肯定不需要执行溢出检验的。
            if pop_node.node_type == "FunctionCall":
                continue
            count = 0
            # 为了可以走循环的节点，但是又不会陷入死循环，设置可以出现的最大重复次数。
            for route in route_already_taken:
                if route == pop_node:
                    count += 1
            if count >= 2:
                continue
            route_already_taken.append(pop_node)
            # 判断当前节点的子节点中是否含有Assignment节点，也就是判断这个节点是不是用于赋值操作。
            for child in pop_node.childes:
                if child.node_type == "Assignment":
                    left_hand_side_name = child.attribute['leftHandSide'][0]["name"]
                    # 如果左边还没有被更新过。
                    if the_left_argument_updates_the_flag is False:
                        # 遍历操作符下所有的参数的名字，看看是否和left_hand_side_name重名，如果重名了，就代表是更新了。
                        for var in operation_obj_list[0]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_left_argument_updates_the_flag = True
                    # 如果右边还没有被使用过。
                    if not the_right_argument_updates_the_flag:
                        for var in operation_obj_list[1]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_right_argument_updates_the_flag = True
                    # 如果赋值目标还没有被使用过
                    if not the_target_updates_the_flag:
                        for var in assignment_node_list:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                if var_name == left_hand_side_name:
                                    the_target_updates_the_flag = True
            # 说明左右的内容都已经被重新赋值了，或者是目标被赋值了,肯定是有问题的。
            if (the_left_argument_updates_the_flag and the_right_argument_updates_the_flag) or the_target_updates_the_flag:
                return True
            # 如果是require或者assert类型,那就说明是断言语句了。
            if pop_node.node_type == "require" or pop_node.node_type == "assert":
                # 如果左边确实没有重新赋值过。
                if the_left_argument_updates_the_flag is False:
                    # 1.判断左边是不是都出现了,先判断所有的参数是不是都在。
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[0]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if not child_of_res.attribute["name"][0] in expression:
                                the_left_parameter_has_unused_content = True
                                break
                # 如果右边确实没有重新赋值过。
                if the_right_argument_updates_the_flag is False:
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[1]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if child_of_res.attribute["name"][0] not in expression:
                                the_right_parameter_has_unused_content = True
                                break
                # 如果目标确实没有重新赋值过
                if the_target_updates_the_flag is False:
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_assignment_node_list in assignment_node_list:
                        if "name" in child_of_assignment_node_list.attribute.keys():
                            # 如果目标名字确实没有出现过。
                            if child_of_assignment_node_list.attribute["name"][0] not in expression:
                                the_target_has_unused_content = True
                                break
                # 如果左边没有被更新过，同时也没有未出现的单词，才能进行target的判断。右边同理。
                if (the_left_argument_updates_the_flag is False and the_left_parameter_has_unused_content is False) or (the_left_argument_updates_the_flag is False and the_right_parameter_has_unused_content is False):
                    # 如果assignment的内容也出现在了expression中，说明这种情况是合理的，是符合条件的，所以暂时略过，而不返回值，进行下一个控制流的循环。
                    if the_target_updates_the_flag is False and the_target_has_unused_content is False:
                        pass_flag = True
                        pass_flag_count += 1
                    else:
                        return True
                else:
                    return True
            # 如果还没有找到目标断言，那就继续往后找。
            if pass_flag is False:
                for control_child in pop_node.control_childes:
                    stack.put(control_child)
            # 都已经找到目标断言了，可以停下来了
            else:
                break
        # 说明在本条路上没有找到乱赋值，断言中变量不足的情况，但是也不代表找到了合适的断言，所以就是错误的。
        if pass_flag is False:
            return True
    # 如果在上面的控制流路线中都已经找到了对应的require，那就直接返回False。
    if pass_flag_count == len(control_node.control_childes) and pass_flag_count > 0:
        return False
    else:
        return True


# 根据目标的控制流节点，获取倒退的控制流路线，判断路线上是否存在断言语句，这里有一个简单的地方，就是只能有一条路线。
def the_value_has_been_updated_without_an_assertion_sub(operation_obj_list, control_node):
    pass_flag_count = 0
    tmp_node = control_node
    while tmp_node.node_type != "FunctionDefinition":
        tmp_node = tmp_node.parent
    function_definition_node = tmp_node
    routes = []
    now_paths = []
    get_all_control_flow_routes_based_on_function_definition_nodes(control_node, function_definition_node, routes, now_paths)
    for route in routes:
        # 每一条控制流路线上的标记都得刷新,代表在断言之前是否被更新过。
        the_left_argument_updates_the_flag = False
        the_right_argument_updates_the_flag = False
        # 判断左边的参数是不是有未出现的，一开始是False，如果查到了有，那就是True。
        the_left_parameter_has_unused_content = False
        the_right_parameter_has_unused_content = False
        # 沿着逆着的方向进行遍历。
        for pop_node in route[::-1]:
            # 遍历当前节点子节点，以判断是不是赋值节点。
            for child in pop_node.childes:
                if child.node_type == "Assignment":
                    left_hand_side_name = child.attribute['leftHandSide'][0]["name"]
                    # 如果左边还没有被使用过。
                    if not the_left_argument_updates_the_flag:
                        for var in operation_obj_list[0]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_left_argument_updates_the_flag = True
                    # 如果右边还没有被使用过。
                    if not the_right_argument_updates_the_flag:
                        for var in operation_obj_list[1]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_right_argument_updates_the_flag = True
            # 说明左右的内容有被赋值过的迹象，肯定是有问题的。
            if the_left_argument_updates_the_flag or the_right_argument_updates_the_flag:
                return True
            # 如果是require或者assert类型,那就说明是断言语句了。
            if pop_node.node_type == "require" or pop_node.node_type == "assert":
                # 如果左边确实没有重新赋值过。
                if the_left_argument_updates_the_flag is False:
                    # 1.判断左边是不是都出现了,先判断所有的参数是不是都在。
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[0]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if not child_of_res.attribute["name"][0] in expression:
                                the_left_parameter_has_unused_content = True
                                break
                # 如果右边确实没有重新赋值过。
                if the_right_argument_updates_the_flag is False:
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[1]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if not child_of_res.attribute["name"][0] in expression:
                                the_right_parameter_has_unused_content = True
                                break
                # 如果左边没有被更新过，同时也没有未出现的单词，才能进行target的判断。右边同理。
                if (the_left_argument_updates_the_flag is False and the_left_parameter_has_unused_content is False) and (the_left_argument_updates_the_flag is False and the_right_parameter_has_unused_content is False):
                    # 那就是说这条路上是安全的，可以直接跳过后面的判断了。
                    # 计算有几条路是ok了。
                    pass_flag_count += 1
                    break
                else:
                    return True
    # 遍历了所有的路线，都没有发现有在require之后更新的地方，那就返回False代表没有漏洞。
    if pass_flag_count == len(routes):
        return False
    # 返回True，代表存在漏洞，因为其中某些路径没有找到断言。
    else:
        return True


# 获取从函数定义节点一直到control_node的所有路线
# control_node代表终点
# now_node代表当前遍历到的位置
# routes代表已经遍历到终点的位置。
# now_paths代表当前已经走过的路线。
def get_all_control_flow_routes_based_on_function_definition_nodes(control_node, now_node, routes, now_paths):
    flag = 0
    for path_node in now_paths:
        if now_node == path_node:
            flag += 1
    # 可以有一次重复，但是不能有第二次是为了有循环。
    # 另外，如果是FunctionCall节点需要直接掉头，因为这个方向不可以走。
    if flag == 2 or now_node.node_type == "FunctionCall":
        return
    if now_node == control_node:
        routes.append(list(now_paths))
    else:
        for control_child in now_node.control_childes:
            # 走下一步路，压入新节点
            now_paths.append(now_node)
            # 进行下一步的操作，目标不变，但是当前位置发生了改变，总路线暂时不变，当前已经走过的路发生了改变。
            get_all_control_flow_routes_based_on_function_definition_nodes(control_node, control_child, routes, now_paths)
            # 回退一步，弹出新节点。
            now_paths.pop(-1)


# 根据目标的控制流节点，获取倒退的控制流路线，判断路线上是否存在断言语句，这里有一个简单的地方，就是只能有一条路线。
def the_value_has_been_updated_without_an_assertion_mul(operation_obj_list, assignment_node_list, control_node):
    pass_flag_count = 0
    tmp_node = control_node
    while tmp_node.node_type != "FunctionDefinition":
        tmp_node = tmp_node.parent
    function_definition_node = tmp_node
    routes = []
    now_paths = []
    get_all_control_flow_routes_based_on_function_definition_nodes(control_node, function_definition_node, routes, now_paths)
    for route in routes:
        # 每一条控制流路线上的标记都得刷新,代表在断言之前是否被更新过。
        the_left_argument_updates_the_flag = False
        the_right_argument_updates_the_flag = False
        # 判断左边的参数是不是有未出现的，一开始是False，如果查到了有，那就是True。
        the_left_parameter_has_unused_content = False
        the_right_parameter_has_unused_content = False
        already_has_an_assertion_that_equals_zero = False
        # 沿着逆着的方向进行遍历。
        for pop_node in route[::-1]:
            # 遍历当前节点子节点，以判断是不是赋值节点。
            for child in pop_node.childes:
                if child.node_type == "Assignment":
                    left_hand_side_name = child.attribute['leftHandSide'][0]["name"]
                    # 如果左边还没有被使用过。
                    if not the_left_argument_updates_the_flag:
                        for var in operation_obj_list[0]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_left_argument_updates_the_flag = True
                    # 如果右边还没有被使用过。
                    if not the_right_argument_updates_the_flag:
                        for var in operation_obj_list[1]:
                            if "name" in var.attribute.keys():
                                var_name = var.attribute["name"][0]
                                # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                if left_hand_side_name == var_name:
                                    the_right_argument_updates_the_flag = True
            # 只有左右都被赋值过才有异常
            if the_left_argument_updates_the_flag and the_right_argument_updates_the_flag:
                return True
            # 如果是require或者assert类型,那就说明是断言语句了。
            if pop_node.node_type == "require" or pop_node.node_type == "assert":
                # 如果左边确实没有重新赋值过。
                if the_left_argument_updates_the_flag is False:
                    # 1.判断左边是不是都出现了,先判断所有的参数是不是都在。
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[0]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if not child_of_res.attribute["name"][0] in expression:
                                the_left_parameter_has_unused_content = True
                                break
                # 如果右边确实没有重新赋值过。
                if the_right_argument_updates_the_flag is False:
                    expression = pop_node.attribute['src_code'][0]
                    for child_of_res in operation_obj_list[1]:
                        # 如果是有名字的
                        if "name" in child_of_res.attribute.keys():
                            # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                            if not child_of_res.attribute["name"][0] in expression:
                                the_right_parameter_has_unused_content = True
                                break
                # 如果左边没有被更新过，同时也没有未出现的单词，才能进行target的判断。右边同理。
                if (the_left_argument_updates_the_flag is False and the_left_parameter_has_unused_content is False) or (the_left_argument_updates_the_flag is False and the_right_parameter_has_unused_content is False):
                    expression = pop_node.attribute['src_code'][0]
                    # 如果这一行代码还包含了==0，那就说明是预判断是不是含有0的断言了。
                    if expression.replace(" ", "").__contains__("==0"):
                        already_has_an_assertion_that_equals_zero = True
                        break
                    else:
                        return True
                else:
                    return True
        # 接下来开始下游的判断。
        # 开始遍历控制流,这里使用遍历是因为为了避免有分岔路。
        for start_control_path in control_node.control_childes:
            # 每一条控制流路线上的标记都得刷新,代表在断言之前是否被更新过。
            the_left_argument_updates_the_flag = False
            the_right_argument_updates_the_flag = False
            the_target_updates_the_flag = False
            # 判断左边的参数是不是有未出现的，一开始是False，如果查到了有，那就是True。
            the_left_parameter_has_unused_content = False
            the_right_parameter_has_unused_content = False
            the_target_has_unused_content = False
            # 一条控制流路线上的是否有符合条件的require已经被找到了。
            pass_flag = False
            # 对这条路进行深度遍历，找出其中不合理的位置。
            stack = LifoQueue(maxsize=0)
            stack.put(start_control_path)
            route_already_taken = []
            while not stack.empty():
                pop_node = stack.get()
                # 如果是FunctionCall节点，这个方向是禁止的方向，掉头。
                if pop_node.node_type == "FunctionCall":
                    continue
                count = 0
                # 为了可以走循环的节点，但是又不会陷入死循环，设置可以出现的最大重复次数。
                for route_node in route_already_taken:
                    if route_node == pop_node:
                        count += 1
                if count >= 2:
                    continue
                route_already_taken.append(pop_node)
                # 判断当前节点的子节点中是否含有Assignment节点，也就是判断这个节点是不是用于赋值操作。
                for child in pop_node.childes:
                    if child.node_type == "Assignment":
                        left_hand_side_name = child.attribute['leftHandSide'][0]["name"]
                        # 如果左边还没有被使用过。
                        if not the_left_argument_updates_the_flag:
                            for var in operation_obj_list[0]:
                                if "name" in var.attribute.keys():
                                    var_name = var.attribute["name"][0]
                                    # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                    if left_hand_side_name == var_name:
                                        the_left_argument_updates_the_flag = True
                        # 如果右边还没有被使用过。
                        if not the_right_argument_updates_the_flag:
                            for var in operation_obj_list[1]:
                                if "name" in var.attribute.keys():
                                    var_name = var.attribute["name"][0]
                                    # 如果两个名字相同，说明被重新赋值了，而此时还没有进行断言操作所以是有问题的。
                                    if left_hand_side_name == var_name:
                                        the_right_argument_updates_the_flag = True
                        # 如果赋值目标还没有被使用过
                        if not the_target_updates_the_flag:
                            for var in assignment_node_list:
                                if "name" in var.attribute.keys():
                                    var_name = var.attribute["name"][0]
                                    if var_name == left_hand_side_name:
                                        the_target_updates_the_flag = True
                # 说明左右的内容都已经被重新赋值了，或者是目标被赋值了,肯定是有问题的。
                if the_left_argument_updates_the_flag or the_right_argument_updates_the_flag or the_target_updates_the_flag:
                    return True
                # 如果是require或者assert类型,那就说明是断言语句了。
                if pop_node.node_type == "require" or pop_node.node_type == "assert":
                    # 如果左边确实没有重新赋值过。
                    if the_left_argument_updates_the_flag is False:
                        # 1.判断左边是不是都出现了,先判断所有的参数是不是都在。
                        expression = pop_node.attribute['src_code'][0]
                        for child_of_res in operation_obj_list[0]:
                            # 如果是有名字的
                            if "name" in child_of_res.attribute.keys():
                                # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                                if not child_of_res.attribute["name"][0] in expression:
                                    the_left_parameter_has_unused_content = True
                                    break
                    # 如果右边确实没有重新赋值过。
                    if the_right_argument_updates_the_flag is False:
                        expression = pop_node.attribute['src_code'][0]
                        for child_of_res in operation_obj_list[1]:
                            # 如果是有名字的
                            if "name" in child_of_res.attribute.keys():
                                # 如果这个变量没有出现过，那就能跳出循环了，同时修改变量。
                                if not child_of_res.attribute["name"][0] in expression:
                                    the_right_parameter_has_unused_content = True
                                    break
                    # 如果目标确实没有重新赋值过
                    if the_target_updates_the_flag is False:
                        expression = pop_node.attribute['src_code'][0]
                        for child_of_assignment_node_list in assignment_node_list:
                            if "name" in child_of_assignment_node_list.attribute.keys():
                                if child_of_assignment_node_list.attribute["name"][0] not in expression:
                                    the_target_has_unused_content = True
                                    break
                    # 只有两种参数还有赋值都没有被更新过，而且都在require中使用了，才有资格进行下一步操作。
                    if (the_left_argument_updates_the_flag is False and the_left_parameter_has_unused_content is False) and (the_left_argument_updates_the_flag is False and the_right_parameter_has_unused_content is False) and (the_target_updates_the_flag is False and the_target_has_unused_content is False):
                        # 如果已经有了==0的判断，那么这里就已经充分了，可以直接令pass_flag = True
                        if already_has_an_assertion_that_equals_zero:
                            pass_flag_count += 1
                            pass_flag = True
                        else:
                            # 如果没有==0的判断，那就在当前行进行判断。
                            expression = pop_node.attribute['src_code'][0]
                            if expression.replace(" ", "").__contains__("==0"):
                                pass_flag_count += 1
                                pass_flag = True
                            else:
                                return True
                    else:
                        return True
                # 如果还没有找到目标断言，那就继续往后找。
                if pass_flag is False:
                    for control_child in pop_node.control_childes:
                        stack.put(control_child)
                else:
                    break
            # 说明在本条路上没有找到乱赋值，断言中变量不足的情况，但是也不代表找到了合适的断言，所以就是错误的。
            if pass_flag is False:
                return True
    # 需要里面每一条路线都是符合条件的，才能证明是安全的，注意这里用上游而不是下游。
    if pass_flag_count == len(routes):
        return False
    else:
        return True
