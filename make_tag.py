from queue import LifoQueue
import config
import json
import os


# 为当前的文件打上是否含有漏洞的标签。
def make_tag(project_node_list, project_node_dict, file_name):
    flag = reentry_attack(project_node_list, project_node_dict, file_name)
    if flag:
        update_label_file(file_name, 1)
    else:
        update_label_file(file_name, 0)
    print(f"{file_name}标签已经打上了。")


# 判断当前的文件中是否含有重入攻击，如果有那么返回True，否则返回False。
def reentry_attack(project_node_list, project_node_dict, file_name):
    # 一个文件中只会含有一个WithdrawFunction用来代表外部合约中的Withdraw函数，如果有，说明当前的合约中含有call.value的部分，否则不会含有。
    if "WithdrawFunction" in project_node_dict.keys():
        withdraw_function_node = project_node_dict["WithdrawFunction"][0]
        # 找到对应的call.value语句，因为是他导致了withdraw节点。
        function_call_node = get_node_by_child_and_node_type_of_target(project_node_list, project_node_dict, withdraw_function_node, "FunctionCall", 2)
        # 去获取他使用的参数的详细信息,这里取出来的父节点已经是只有一个，所以可以大胆取元素0
        argument_node_node_id = function_call_node[0].attribute["arguments"][0][0]["id"]
        argument_node_node_type = function_call_node[0].attribute["arguments"][0][0]["nodeType"]
        # 根据参数的详细信息取到对应的节点。
        for child_of_function_call_node in function_call_node[0].childes:
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
