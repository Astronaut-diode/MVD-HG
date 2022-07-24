from queue import LifoQueue
import config
import json
import os


# 为当前的文件打上是否含有漏洞的标签。
def make_tag(project_node_list, project_node_dict, file_name):
    # 如果是generate_all，可以不走这个函数了，因为一开始create_corpus_txt的时候已经走过了。
    if config.create_corpus_mode == "generate_all":
        return
    if reentry_attack(project_node_list, project_node_dict, file_name):
        reentry_flag = 1
    else:
        reentry_flag = 0
    if timestamp_attack(project_node_list, project_node_dict, file_name):
        timestamp_flag = 1
    else:
        timestamp_flag = 0
    label = [reentry_flag, timestamp_flag]
    update_label_file(file_name, label)
    print(f"{file_name}标签已经打上了。")


# 通过目标节点的节点类型以及子节点,但是还需要判断属于哪种子节点，来找到目标节点,根据这两个条件，找到的节点，依然可能是多个，需要继续筛选，所以用list。
# 注意，如果用的是数据流，那节点类型就不用了，直接用默认的参数。
# type_flag:1代表是抽象语法树子节点，2代表是控制流子节点，3代表是数据流子节点
def get_node_by_child_and_node_type_of_target(project_node_list, project_node_dict, child, node_type, type_flag):
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
        if node in res:
            continue
        res.append(node)
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
                if is_method and child.attribute["src_code"] in ["transfer", "send", "call.value"]:
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
def reentry_attack(project_node_list, project_node_dict, file_name):
    # 一个文件中只会含有一个WithdrawFunction用来代表外部合约中的Withdraw函数，如果有，说明当前的合约中含有call.value的部分，否则不会含有。
    if "WithdrawFunction" in project_node_dict.keys():
        withdraw_function_node = project_node_dict["WithdrawFunction"][0]
        # 找到对应的call.value语句，因为是他导致了withdraw节点。
        function_call_node = get_node_by_child_and_node_type_of_target(project_node_list, project_node_dict, withdraw_function_node, "FunctionCall", 2)
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
                    # 代码所处的位置，如果发现后面辐射的位置有比这个大的，那就说明是有重入的危险。
                    code_index = argument_node.attribute["src"][0].split(":")[0]
                    # 代表和当前的这个参数等同效力的参数列表。
                    equal_list = [argument_node]
                    now_node = argument_node
                    while True:
                        # 根据当前节点，去寻找数据流的父节点是谁。
                        res = get_node_by_child_and_node_type_of_target(project_node_list, project_node_dict, now_node, None, 3)
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
                        if tmp_code_index > code_index:
                            return True
                        else:
                            already_dfs_list.append(pop_node)
                            for child_of_pop_node in pop_node.data_childes:
                                # 注意，如果是FunctionCall节点记得要停下来，因为大概率调用函数以后的参数和当前其实没什么关系，或者说是一种映射关系，对当前的查询没有意义。
                                if child_of_pop_node.node_type != "FunctionCall":
                                    stack.put(child_of_pop_node)
    # 一直没有找到，当然是返回False了。
    return False


def timestamp_attack(project_node_list, project_node_dict, file_name):
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
