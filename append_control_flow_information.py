# coding=UTF-8
from queue import LifoQueue, Queue
from bean.Node import Node


# 在工程文件夹内容全部读取完毕以后，传入生成的节点列表和节点字典，来为所有的节点添加控制流的边，此时的FunctionDefinition节点已经拥有了自己的method_name和params的参数。
# 第一趟：直接将所有的整句的句子先连接起来，因为Block中一定不会含有FunctionCall节点。
def append_control_flow_information(project_node_list, project_node_dict, data_sol_source_project_dir_path):
    # 设定待会进行遍历的容器。
    stack = LifoQueue(maxsize=0)
    # 记录哪些节点是已经连接好了的，不需要再发生变动的。
    already_connected_node_list = []
    # 禁止再被连接的节点列表
    ban_node_list = []
    # 代表在每一个FunctionDefinition节点中最后一句是谁，先不用管函数调用的情况，保存的格式是字典形式。{FunctionDefinitionNode: LastChildesNode}
    last_command_in_function_definition_node = {}
    if 'FunctionDefinition' in project_node_dict.keys():
        # 从节点字典中取出所有的FunctionDefinition节点，对每一个FunctionDefinition节点进行操作。
        for function_definition_node in project_node_dict['FunctionDefinition']:
            # 先设定每一个函数的最后一句是自己，因为有的函数可能是空的函数体。
            last_command_in_function_definition_node[function_definition_node] = [function_definition_node]
            # 将这个FunctionDefinition节点压入栈中，作为遍历的根节点。
            stack.put(function_definition_node)
            # 如果栈不是空的，就一直进行遍历，因为当前函数还有内容没有被操作完。
            while not stack.empty():
                # 不断地从栈中取出内容进行下一步的连接操作，并将下一个节点重新压入到栈中。
                pop_node = stack.get()
                if pop_node in already_connected_node_list or pop_node is None:
                    continue
                # 根据节点的类型进行不同的操作，注意，这里永远不会出现虚拟节点，哪怕出现也没关系，因为不会有对应的操作。
                if pop_node.node_type == "FunctionDefinition":
                    function_definition_type_link_next_node(pop_node, project_node_dict, stack, already_connected_node_list)
                elif pop_node.node_type == "IfStatement":
                    if_statement_type_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "ExpressionStatement":
                    expression_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list, project_node_dict)
                elif pop_node.node_type == "VariableDeclarationStatement":
                    variable_declaration_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "ForStatement":
                    for_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "WhileStatement":
                    while_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "DoWhileStatement":
                    do_while_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "Break":
                    break_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "Continue":
                    continue_link_next_node(pop_node, stack, already_connected_node_list)
                elif pop_node.node_type == "RevertStatement":
                    revert_statement_link_next_node(pop_node, stack, already_connected_node_list, project_node_dict)
                elif pop_node.node_type == "Return":
                    return_link_next_node(pop_node, already_connected_node_list)
    # 如果确实存在修饰符
    if "ModifierDefinition" in project_node_dict.keys():
        # 循环其中每一个修饰符节点。
        for modifier_definition_node in project_node_dict['ModifierDefinition']:
            # 先设定每一个修饰符的最后一句是自己，因为有的函数可能是空的函数体。
            last_command_in_function_definition_node[modifier_definition_node] = [modifier_definition_node]
            # 将这个ModifierDefinition节点压入栈中，作为遍历的根节点。
            stack.put(modifier_definition_node)
            # 如果栈不是空的，就一直进行遍历，因为当前函数还有内容没有被操作完。
            while not stack.empty():
                pop_node = stack.get()
                # 如果已经查询过了就先跳过。
                if pop_node is None or pop_node in already_connected_node_list:
                    continue
                # 根据节点的类型进行不同的操作，注意，这里永远不会出现虚拟节点，哪怕出现也没关系，因为不会有对应的操作。
                if pop_node.node_type == "ModifierDefinition":
                    modifier_definition_node_link_next_node(pop_node, stack, already_connected_node_list)
                elif pop_node.node_type == "IfStatement":
                    if_statement_type_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "ExpressionStatement":
                    expression_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list, project_node_dict)
                elif pop_node.node_type == "VariableDeclarationStatement":
                    variable_declaration_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "ForStatement":
                    for_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "WhileStatement":
                    while_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "DoWhileStatement":
                    do_while_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "Break":
                    break_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "Continue":
                    continue_link_next_node(pop_node, stack, already_connected_node_list)
                elif pop_node.node_type == "PlaceholderStatement":
                    placeholder_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
                elif pop_node.node_type == "Return":
                    return_link_next_node(pop_node, already_connected_node_list)
    # 在所有的连接完成以后，删除所有的虚拟节点
    if "ForStatement" in project_node_dict.keys():
        for for_statement_node in project_node_dict['ForStatement']:
            for index, node in enumerate(for_statement_node.childes):
                if node.node_type == "virtue_node":
                    # 删除这个子节点
                    del for_statement_node.childes[index]
                    # 删除这个虚拟节点的下游边
                    del node.control_childes[0]
    # 如果确实存在FunctionDefinition键。
    if 'FunctionDefinition' in project_node_dict.keys():
        # 如何获取每一个functionDefinition节点下面的最后一句话
        for function_definition_node in project_node_dict['FunctionDefinition']:
            # 获取这个函数定义节点子范围内的最后一句，以数组的形式返回。
            res = get_last_command_at_function(function_definition_node)
            # 如果其中确实是含有内容的，可以直接将这个内容用来覆盖原始的最后一句话数组。
            if len(res) > 0:
                last_command_in_function_definition_node[function_definition_node] = res
            # 否则，说明该函数极有可能是空函数，默认使用函数名作为最后一句话。
            else:
                pass
    # 如果确实存在修饰符的键。
    if 'ModifierDefinition' in project_node_dict.keys():
        # 获取每个modifierDefinition节点下的最后一句话。
        for modifier_definition_node in project_node_dict['ModifierDefinition']:
            # 获取这个函数定义节点子范围内的最后一句，以数组的形式返回。
            res = get_last_command_at_function(modifier_definition_node)
            # 如果其中确实是含有内容的，可以直接将这个内容用来覆盖原始的最后一句话数组。
            if len(res) > 0:
                last_command_in_function_definition_node[modifier_definition_node] = res
            # 否则，说明该函数极有可能是空函数，默认使用函数名作为最后一句话。
            else:
                pass
    # 如果确实存在FunctionCall这个字段，说明才有可能可以连接。
    if "FunctionCall" in project_node_dict.keys():
        # 实现FunctionCall和FunctionDefinition的连接。
        for node in project_node_dict['FunctionCall']:
            # 如果没有这个字段，说明是外部调用的函数，不需要连接。
            if 'referencedDeclaration' in node.attribute['expression'][0]:
                # 这个id就是对应的FunctionDefinition节点的id
                call_function_node_id = node.attribute['expression'][0]['referencedDeclaration']
                # 可能调用的是外部的函数，所以不会存在内部函数，也就是没有这个键。
                if 'FunctionDefinition' in project_node_dict.keys():
                    for tmp_to_find_function_definition_node in project_node_dict['FunctionDefinition']:
                        # 如果FunctionCall中使用的referencedDeclaration和节点的id一致，说明就是调用了这个FunctionDefinition节点。
                        if tmp_to_find_function_definition_node.node_id == call_function_node_id:
                            # 先将FunctionCall连接到对应的FunctionDefinition上
                            node.append_control_child(tmp_to_find_function_definition_node)
                            # 找出这个FunctionDefinition节点的最后一句话
                            last_command = last_command_in_function_definition_node[tmp_to_find_function_definition_node]
                            # 将最后一句话连回到FunctionCall节点上,注意，这里的last_command是一个list，里面的内容很多，需要遍历操作。
                            for command in last_command:
                                command.append_control_child(node)
                            break
    # 如果确实有ModifierDefinition字段，才有可能进行后续操作。
    if "ModifierDefinition" in project_node_dict.keys():
        # 循环其中每一个修饰符函数
        for modifier_definition_node in project_node_dict["ModifierDefinition"]:
            # 获取当前这个修饰符的最后一句是谁。
            last_command = last_command_in_function_definition_node[modifier_definition_node]
            # 遍历这个修饰符的所有控制流子节点，其中是FunctionDefinition节点的全部断掉，然后用最后一个节点连上作为代替。
            # 注意，这里需要使用倒序，才能够删除元素。
            for control_child in modifier_definition_node.control_childes[::-1]:
                # 找到了FunctionDefinition的控制流子节点
                if control_child.node_type == "FunctionDefinition":
                    # 遍历所有的最后一句话，然后连回去。
                    for command in last_command:
                        # 最后一句话们们们们们注意是们，连接到FunctionDefinition节点上
                        command.append_control_child(control_child)
                    # 删除ModifierDefinition和FunctionDefinition连接的边。
                    modifier_definition_node.control_childes.remove(control_child)
    print(f"{data_sol_source_project_dir_path}节点控制流更新成功")


# 找到block节点下面的第一句语句。
def get_first_command_in_block(block_node):
    if block_node is None:
        return None
    next_expression = None
    # 忽略操作的几类节点
    ignore_node_type_list = ['ParameterList', 'TryCatchClause', 'TryStatement', 'TupleExpression', 'UnaryOperation', 'UncheckedBlock', 'UserDefinedTypeName', 'UsingForDirective', 'VariableDeclaration', 'SourceUnit', 'StructDefinition', 'PragmaDirective', 'InlineAssembly', 'OverrideSpecifier', 'EnumDefinition', 'EnumValue', 'ElementaryTypeName', 'ElementaryTypeNameExpression', 'EmitStatement', 'EventDefinition', 'ArrayTypeName', 'Literal', 'Mapping', 'ContractDefinition']
    for child in block_node.childes:
        # 如果发现找到这个节点类型在忽略的类型当中
        if child.node_type in ignore_node_type_list:
            continue
        else:
            next_expression = child
            break
    # 在这里判断结果就行，如果是最后一句，返回的一定是None
    if next_expression is None:
        return None
    # 如果发现找到的结果还是Block节点，那就继续往下面找
    if next_expression.node_type == "Block":
        # 用这个next_expression继续深入查询。
        next_expression = get_first_command_in_block(next_expression)
    # 返回下一句。
    return next_expression


# 找出当前节点的下一句语句,视为普通语句。
def get_next_command_at_now(node, ban_node_list):
    # 父亲节点，上面传入的node是当前节点。
    parent = node.parent
    # 一直查询，如果祖先节点已经到了FunctionDefinition节点，那就说明已经要超出函数范围了，停下来。可以保证只在函数内查询下一句。
    if parent.node_type == "FunctionDefinition" or parent.node_type == "ModifierDefinition":
        return None
    #  如果父节点是If语句，那说明找下一句的时候肯定不会在if的子节点中找了
    if parent.node_type == "IfStatement":
        return get_next_command_at_now(parent, ban_node_list)
    # 返回的结果。
    next_expression = None
    # 忽略操作的几类节点。这里的最前的两种类型是为了避免for循环的最后一句话会连接到初始条件或者判断条件上。
    ignore_node_type_list = ['ParameterList', 'TryCatchClause', 'TryStatement', 'TupleExpression', 'UnaryOperation', 'UncheckedBlock', 'UserDefinedTypeName', 'UsingForDirective', 'VariableDeclaration', 'SourceUnit', 'StructDefinition', 'PragmaDirective', 'InlineAssembly', 'OverrideSpecifier', 'EnumDefinition', 'EnumValue', 'ElementaryTypeName', 'ElementaryTypeNameExpression', 'EmitStatement', 'EventDefinition', 'ArrayTypeName', 'Literal', 'Mapping', 'ContractDefinition']
    has_find_flag = False
    # 只要在父亲节点的子节点中找到当前节点，然后继续往后循环一个元素，如果该元素的类型还不是上面的忽略类型，那就说明那就是下一句。
    for child in parent.childes:
        # 如果已经找到了这个节点，那后面需要做新的操作
        if has_find_flag:
            # 如果传入节点的下一个节点的类型不在忽略操作的类型当中，那就可以了，但是还需要看看怎么用。
            # 同时还要满足不被禁用的情况，都是为了满足for和while的不同需求。
            if child.node_type not in ignore_node_type_list and child not in ban_node_list:
                # 如果是Block需要找出Block的第一句作为下一句
                if child.node_type == "Block":
                    next_expression = get_first_command_in_block(child)
                # 如果是手动设置的虚拟节点，先连上虚拟节点设置好的下游边
                elif child.node_type == "virtue_node":
                    next_expression = child.control_childes[0]
                    break
                # 否则直接当作下一句处理即可。
                else:
                    # 找到了的话就不需要继续往后寻找了。
                    next_expression = child
                    break
        # 还没有找到当前传入的node节点，
        else:
            # 找到了当前节点
            if child == node:
                has_find_flag = True
            else:
                continue
    # 说明兄弟级别的下一句已经没有了，需要去找祖先级别的了。
    if next_expression is None:
        # 获取祖先的下一句，作为当前的下一句。
        next_expression = get_next_command_at_now(parent, ban_node_list)
    # 不管有没有找到结果，都直接返回。
    return next_expression


# 获取function_definition节点子域中的最后一个节点，以数组形式返回。
def get_last_command_at_function(function_definition_node):
    res = set()
    stack = LifoQueue(maxsize=0)
    stack.put(function_definition_node)
    # 只要栈内不是空的，就一直循环。
    while not stack.empty():
        pop_node = stack.get()
        # 条件1:如果控制流子节点只有入度，没有出度，说明该子节点是最终的句子。
        if len(pop_node.control_childes) > 0:
            # 循环其中的每一个控制子节点
            for control_child in pop_node.control_childes:
                # 如果控制流子节点没有自己的控制流子节点作为输出，那说明就是只有入度没有出度的部分。
                if len(control_child.control_childes) == 0:
                    res.add(control_child)
        # 重新压入所有的子节点，做深度遍历dfs
        for child in pop_node.childes:
            stack.put(child)
    # 上面仅仅只是查了条件1，条件和后面的条件不能一起操作，所以分了两个循环。
    stack.put(function_definition_node)
    while not stack.empty():
        pop_node = stack.get()
        # 条件2:判断是不是[Return,require,revert]节点中的,如果是，那当前节点也是终止节点。
        if pop_node.node_type in ['Return', 'require', 'revert']:
            res.add(pop_node)
            continue
        for child in pop_node.childes:
            stack.put(child)
    # 条件3:求出第一个Block的最后一个子节点，判断是不是带有判断语句的部分，如果是，那判断语句也极有可能是最后一句话。
    for block_node in function_definition_node.childes:
        # 确定有子节点
        if len(block_node.childes) > 0:
            # 取出最后一个子节点
            last_node = block_node.childes[-1]
            # 如果是循环节点，而且条件节点是存在的
            if last_node.node_type in ["ForStatement", "WhileStatement", "DoWhileStatement"] and last_node.attribute['condition'][0] is not None:
                condition_node_node_id = last_node.attribute['condition'][0]['id']
                condition_node_node_type = last_node.attribute['condition'][0]['nodeType']
                # 找出其中的三个循环节点。
                for node in last_node.childes:
                    node_id = node.node_id
                    node_type = node.node_type
                    if node_id == condition_node_node_id and node_type == condition_node_node_type:
                        condition_node = node
                        # 那么条件语句节点是有可能成为最后一句的。
                        res.add(condition_node)
            # 如果是if语句，只有一个出度，那就说明会是最终节点了。
            elif last_node.node_type == "IfStatement":
                # 查询其中的block子节点的数量，ifStatement的数量
                block_node_num = 0
                if_statement_node_num = 0
                # 这个节点就是用在判断语句上的节点，但是节点的类型是不固定的，因为可以是函数调用，可以是bool判断也可以是常量True
                target_node = None
                for child in last_node.childes:
                    if child.node_type == "Block":
                        block_node_num = block_node_num + 1
                    elif child.node_type == "IfStatement":
                        if_statement_node_num = if_statement_node_num + 1
                    # 既不是block也不是if，那就是我们的目标，而且只会有一个。
                    else:
                        target_node = child
                # 只有当block数量为1，if数量为0的时候，才能说明是使用的是if{}，可以直接视为最终节点。
                if block_node_num == 1 and if_statement_node_num == 0:
                    res.add(target_node)
    return list(res)


# 找出当前节点的子域中从深处到浅处的functionCall的list列表，直接连起来。
def link_function_call_list_at_now_now(node):
    # 返回的列表,先往里面添加一个初始节点，因为到时候也要添加的，可以方便操作。到时候直接每两个相邻节点直接连边即可。
    res = [node]
    # 使用广度遍历所以使用队列queue
    queue = Queue(maxsize=0)
    queue.put(node)
    while not queue.empty():
        pop_node = queue.get()
        # 先压入子节点，以进行广度遍历
        for child in pop_node.childes:
            queue.put(child)
        # 如果当前节点是FunctionCall节点，记录下来。
        if pop_node.node_type == "FunctionCall":
            res.append(pop_node)
    # 如果大于等于2，那就说明确实有FunctionCall节点被记录下来了，需要建立环。
    if len(res) >= 2:
        # 此时的数组内容应该是[原始node, 第一个FunctionCall，第二个FunctionCall,....,第n个FunctionCall]
        for index, pre_node in enumerate(res):
            # 找出下一个元素，可以使用回环取余的方式获取对应的下标。
            after_node = res[(index + 1) % len(res)]
            pre_node.append_control_child(after_node)


# 如果弹出的节点类型是FunctionDefinition的时候，使用这个函数去找出他的下一句，将他们连接起来，同时将下一句再一次压入到栈中。
# 规则：
# 1.先判断其中是否含有Modifier的调用，如果有就先连Modifier
# 2.否则先连接子节点的Block中第一句，根据第一句的类型不同，连接方法也不同。
def function_definition_type_link_next_node(function_definition_node, project_node_dict, stack, already_connected_node_list):
    # 1.先循环所有的子节点，找出其中使用到的每一个ModifierInvocation,如果存在那就代表使用过修饰符。
    for childes in function_definition_node.childes:
        if childes.node_type == "ModifierInvocation":
            # 取出这个修饰符的名字和id
            used_modifier_name = childes.attribute['modifierName'][0]['name']
            used_modifier_id = childes.attribute['modifierName'][0]['referencedDeclaration']
            # 有用到修饰符不代表一定会有对应的节点，可能用的是默认的。
            if 'ModifierDefinition' in project_node_dict.keys():
                # 根据修饰符的名字和referencedDeclaration去寻找对应的ModifierDefinition节点，并连起来。
                for modifier_definition_node in project_node_dict['ModifierDefinition']:
                    # 当使用的修饰符的id和遍历的修饰符的id对上，以及名字也对上了，说明节点找到了，出于分离业务更加简单的道理，在这里先简单的连上函数或者修饰符的节点，但是不需要去找最后一句是谁。
                    if modifier_definition_node.attribute['name'][0] == used_modifier_name and modifier_definition_node.node_id == used_modifier_id:
                        # 设定好下一句是ModifiedDefinition节点。
                        next_expression = modifier_definition_node
                        # 将这两个节点互相连接起来。
                        function_definition_node.append_control_child(next_expression)
                        next_expression.append_control_child(function_definition_node)
                        # 将下一句压入栈中进行新的操作。
                        stack.put(modifier_definition_node)
                        # 因为我要的内容已经找到了，后续不再操作。
                        break
    # 2.找出FunctionDefinition节点中的Block节点。
    for block_node in function_definition_node.childes:
        # 如果节点的类型是Block,找这个Block下面的第一个节点作为下一句。
        if block_node.node_type == "Block":
            # 如果长度不为0，那就说明里面有东西，取出第一个元素。
            if not len(block_node.childes) == 0:
                # 设定好下一句是当前的Block的第一个子节点。
                next_expression = get_first_command_in_block(block_node)
                # 如果没有，那就直接不要连接了，后面免得出现问题。
                if next_expression is None:
                    continue
                # 将下一句连上来。
                function_definition_node.append_control_child(next_expression)
                # 将下一句压入到栈中，进行新的操作。
                stack.put(next_expression)
            else:
                # 如果没有东西就不需要操作了，所以可以直接空过。
                pass
    # 这个节点已经连接好了，不需要再往外面连接新的边。
    already_connected_node_list.append(function_definition_node)


# 如果弹出的节点是if语句，使用这个函数找出if的下一句，并将他们连起来，同时将下一句压入栈中。注意，这里最多会有两个出度。
# 规则:
# 1.先找出这个节点有几个Block子节点和if，通过这个可以判断出整体的代码情况，是仅if，if ... else,还是 if ... else if ...
# 2.如果是仅if,需要连接if的Block中第一句，连接正常的下一句，按照兄，父的顺序来查询。
# 3.如果是if else，仅需要连接两个Block的第一句。
# 4.如果是if else if,仅需要连接一个Block的第一句还有一个if。
# 以上查询Block中的内容时，如果Block不存在内容，就需要往祖先节点中找。
def if_statement_type_link_next_node(if_statement_node, stack, already_connected_node_list, ban_node_list):
    # 判断条件的节点id和节点类型
    condition_node_node_id = if_statement_node.attribute['condition'][0]['id']
    condition_node_node_type = if_statement_node.attribute['condition'][0]['nodeType']
    condition_node = None
    # 下面这两个next_expression是在block不存在的时候使用的。
    next_expression_1 = None
    next_expression_2 = None
    # if和block的数量
    if_statement_node_num = 0
    block_node_num = 0
    # 当找到这两类节点以后先保存一下，方便后面的操作。
    block_node_list = []
    if_statement_node_list = []
    # 遍历其中所有的子节点，用来计算block子节点和if子节点有多少个。同时将节点的内容添加到数组中。
    for child_of_if_statement_node in if_statement_node.childes:
        if child_of_if_statement_node.node_type == "Block":
            block_node_num = block_node_num + 1
            block_node_list.append(child_of_if_statement_node)
        elif child_of_if_statement_node.node_type == "IfStatement":
            if_statement_node_num = if_statement_node_num + 1
            if_statement_node_list.append(child_of_if_statement_node)
        # 只有id和类型都已经对上了，才能判断为条件节点。
        elif child_of_if_statement_node.node_id == condition_node_node_id and child_of_if_statement_node.node_type == condition_node_node_type:
            condition_node = child_of_if_statement_node
            # if连上binary，后面用binary代替if连剩下的部分即可。
            if_statement_node.append_control_child(condition_node)
        # 如果上面的都不是，那就说明有可能是block里面的内容，但是没有写block
        else:
            if next_expression_1 is None:
                next_expression_1 = child_of_if_statement_node
                block_node_num = block_node_num + 1
            else:
                next_expression_2 = child_of_if_statement_node
                block_node_num = block_node_num + 1
    # 情况1:只有一个if
    if block_node_num == 1 and if_statement_node_num == 0:
        if len(block_node_list) == 1:
            # 1.先做关于Block的工作,这就是那唯一的一个Block节点。
            block_node = block_node_list[0]
            # 设定好下一句是当前的Block的第一个子节点。
            next_expression_1 = get_first_command_in_block(block_node)
        if next_expression_1 is not None:
            condition_node.append_control_child(next_expression_1)
            stack.put(next_expression_1)
        # 2.查询当前if语句的下一句
        next_expression = get_next_command_at_now(if_statement_node, ban_node_list)
        if next_expression is not None:
            condition_node.append_control_child(next_expression)
            stack.put(next_expression)
    # if else 代表有两个block
    elif block_node_num == 2:
        # 找出Block1下面的第一句是谁，然后直接作为if的下一句连接。
        if len(block_node_list) == 2:
            # 分别获取两个block节点，然后获取两个block节点中的第一句
            block_node_1 = block_node_list[0]
            next_expression_1 = get_first_command_in_block(block_node_1)
        if next_expression_1 is not None:
            condition_node.append_control_child(next_expression_1)
            stack.put(next_expression_1)
        # 找出Block2下面的第一句是谁，然后直接作为if的下一句连接。
        if len(block_node_list) == 2:
            # 分别获取两个block节点，然后获取两个block节点中的第一句
            block_node_2 = block_node_list[1]
            next_expression_2 = get_first_command_in_block(block_node_2)
        if next_expression_2 is not None:
            condition_node.append_control_child(next_expression_2)
            stack.put(next_expression_2)
    # 如果两个都是1，说明是if else if...这样的
    elif block_node_num == 1 and if_statement_node_num == 1:
        if len(block_node_list) > 0:
            # 获取其中的Block节点。
            block_node = block_node_list[0]
            # 找出Block下面的第一句，直接作为ifStatement的下一句。
            next_expression_1 = get_first_command_in_block(block_node)
        if next_expression_1 is not None:
            condition_node.append_control_child(next_expression_1)
            stack.put(next_expression_1)
        # 获取其中的if节点
        next_expression = if_statement_node_list[0]
        # 这里获取的ifStatement一定不会空
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 这两个点的出度都已经配置完成，不需要进行新的操作。
    already_connected_node_list.append(if_statement_node)
    already_connected_node_list.append(condition_node)


# 当遇到的结果是ExpressionStatement节点的时候使用的方法。
# 规则，直接去找下一句进行连接。
def expression_statement_link_next_node(expression_statement_node, stack, already_connected_node_list, ban_node_list, project_node_dict):
    # 如果含有expression这个key，这说明有可能是函数调用。
    if 'expression' in expression_statement_node.attribute['expression'][0].keys():
        # 如果里面还含有name字段，那说明是函数调用的概率更大了。
        if 'name' in expression_statement_node.attribute['expression'][0]['expression'].keys():
            # 如果使用的是这几类函数，需要创建新的节点类型。
            if expression_statement_node.attribute['expression'][0]['expression']['name'] in ['revert', 'require']:
                # 修改节点类型
                expression_statement_node.node_type = expression_statement_node.attribute['expression'][0]['expression']['name']
                # 修改在节点类型字典中的存在。
                index = project_node_dict['ExpressionStatement'].index(expression_statement_node)
                # 先删除原有的expressionStatement字典中的部分
                del project_node_dict['ExpressionStatement'][index]
                # 如果这个字段已经存在了，那就直接添加
                if expression_statement_node.node_type in project_node_dict.keys():
                    # 添加新的节点到对应的属性上
                    project_node_dict[expression_statement_node.node_type].append(expression_statement_node)
                # 否则创建一个新的数组，同时添加内容。
                else:
                    project_node_dict[expression_statement_node.node_type] = [expression_statement_node]
    # 连接当前节点下面所有的FunctionCall节点。
    link_function_call_list_at_now_now(expression_statement_node)
    next_expression = get_next_command_at_now(expression_statement_node, ban_node_list)
    if next_expression is not None:
        expression_statement_node.append_control_child(next_expression)
        stack.put(next_expression)
    already_connected_node_list.append(expression_statement_node)


# 当遇到了VariableDeclarationStatement节点的时候使用的方法。
# 规则，直接找出当前句子的下一句进行连接。
def variable_declaration_statement_link_next_node(variable_declaration_statement_node, stack, already_connected_node_list, ban_node_list):
    next_expression = get_next_command_at_now(variable_declaration_statement_node, ban_node_list)
    # 连接其中所有的FunctionCall节点。
    link_function_call_list_at_now_now(variable_declaration_statement_node)
    if next_expression is not None:
        variable_declaration_statement_node.append_control_child(next_expression)
        stack.put(next_expression)
    already_connected_node_list.append(variable_declaration_statement_node)


# 当遇到了ForStatement节点的时候使用的方法
# 规则:先找出对应的四种节点，分别是赋值，判断，循环，还有循环体
# 1.for节点->init->condition->body第一句
# 2.body最后一句连接loop不需要写.
def for_statement_link_next_node(for_statement_node, stack, already_connected_node_list, ban_node_list):
    # 从for_statement_node中找出以下的几部分信息，可以作为连接三个条件的判断条件。
    # 这里的三个条件都要判断一下是否为空
    # 如果初始条件不存在
    if 'initializationExpression' not in for_statement_node.attribute.keys() or for_statement_node.attribute['initializationExpression'][0] is None:
        # 设定id和type都为none，这样就不会找到内容
        initialization_expression_node_node_id = None
        initialization_expression_node_node_type = None
        # 因为找不到节点，所以需要先创建一个虚拟节点代替一下。
        initialization_expression_node = Node(for_statement_node.node_id + 1, "virtue_node", None)
    else:
        initialization_expression_node_node_id = for_statement_node.attribute['initializationExpression'][0]['id']
        initialization_expression_node_node_type = for_statement_node.attribute['initializationExpression'][0]['nodeType']
        initialization_expression_node = None
    # 如果循环条件不存在
    if 'loopExpression' not in for_statement_node.attribute.keys() or for_statement_node.attribute['loopExpression'][0] is None:
        # 设定id和type都是None，这样就不会找到对应的节点
        loop_expression_node_node_id = None
        loop_expression_node_node_type = None
        # 因为找不到对应的节点，所以需要先创建一个虚拟节点代替一下。这里设置parent是为了删除的时候方便找到上级节点。
        loop_expression_node = Node(for_statement_node.node_id + 2, "virtue_node", for_statement_node)
        # 这个虚拟节点比较特殊，需要设定为子节点，方便在遇到了Continue的时候直接找到当前这个虚拟节点。
        for_statement_node.append_child(loop_expression_node)
    else:
        loop_expression_node_node_id = for_statement_node.attribute['loopExpression'][0]['id']
        loop_expression_node_node_type = for_statement_node.attribute['loopExpression'][0]['nodeType']
        loop_expression_node = None
    # 如果判断条件不存在
    if 'condition' not in for_statement_node.attribute.keys() or for_statement_node.attribute['condition'][0] is None:
        # 设定id和type都是None，这样就不会找到对应的节点。
        condition_node_node_id = None
        condition_node_node_type = None
        # 因为找不到对应的节点，所以先创建虚拟节点代替一下。
        condition_node = Node(for_statement_node.node_id + 3, "virtue_node", None)
    else:
        condition_node_node_id = for_statement_node.attribute['condition'][0]['id']
        condition_node_node_type = for_statement_node.attribute['condition'][0]['nodeType']
        condition_node = None
    # 循环体的节点。
    block_node = None
    next_expression = None
    # 找出其中的三个循环节点。
    for node in for_statement_node.childes:
        node_id = node.node_id
        node_type = node.node_type
        # 说明当前找到的是initializationExpression的节点。
        if node_id == initialization_expression_node_node_id and node_type == initialization_expression_node_node_type:
            initialization_expression_node = node
        # 说明当前找到的是loopExpression的节点。
        elif node_id == loop_expression_node_node_id and node_type == loop_expression_node_node_type:
            loop_expression_node = node
        # 说明找到的是condition的节点。
        elif node_id == condition_node_node_id and node_type == condition_node_node_type:
            condition_node = node
        # 如果是Block说明是循环体
        elif node.node_type == "Block":
            block_node = node
        # 如果没有Block那就说明这份代码中的循环只有一句话，没有多行。
        else:
            next_expression = node
    # 下面不管节点是否存在，因为创建了虚拟节点进行代替，所以可以直接使用。
    # 1.连接for循环和第一句初始化句子
    for_statement_node.append_control_child(initialization_expression_node)
    # 2.连接第一句初始化句子和判断语句。
    initialization_expression_node.append_control_child(condition_node)
    # 说明循环体中没有使用{}括起来
    if block_node is not None:
        # 3.连接判断语句和循环体block中的第一句，这里不需要判断是不是虚拟节点，因为这里连接的边在下边是需要用到的。
        next_expression = get_first_command_in_block(block_node)
    # 记住:只有非空的时候才能连接
    if next_expression is not None:
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 4.最后一句连接到loop上，这个不需要写，最后一句自然会找到loop节点的。
    # 5.连接loop和condition
    loop_expression_node.append_control_child(condition_node)
    # 如果condition节点不是虚拟节点，才有资格外连。
    if not condition_node.node_type == "virtue_node":
        # 6.找出和for循环齐平的下一句句子是谁，然后用condition进行连接。
        next_expression = get_next_command_at_now(for_statement_node, ban_node_list)
        if next_expression is not None:
            condition_node.append_control_child(next_expression)
            stack.put(next_expression)
    # 判断谁是虚拟节点，如果有虚拟节点，一一断开，重新连接。
    # 如果判断节点是虚拟节点
    if condition_node.node_type == "virtue_node":
        # 连上init节点和block中的第一句
        initialization_expression_node.append_control_child(condition_node.control_childes[0])
        # 断开init和condition的边
        del initialization_expression_node.control_childes[0]
        # 连上loop节点和block中的第一句
        loop_expression_node.append_control_child(condition_node.control_childes[0])
        # 断开loop和condition的边。
        del loop_expression_node.control_childes[0]
        # 断开虚拟节点的所有的边
        del condition_node.control_childes[0]
    # 如果init节点是虚拟节点
    if initialization_expression_node.node_type == "virtue_node":
        # 先连上for和init连接的子节点。
        for_statement_node.append_control_child(initialization_expression_node.control_childes[0])
        # 断开for和init之间的边
        del for_statement_node.control_childes[0]
        # 断开虚拟节点所有的边
        del initialization_expression_node.control_childes[0]
    # 如果循环节点是虚拟节点，那也暂时不管，先放着，在最后一句或者continue找到了这个节点的时候，多做一步操作，在最后再删除图上所有的虚拟节点。
    # 以下的几个点都已经配置完成，不需要添加新的出度。
    already_connected_node_list.append(for_statement_node)
    already_connected_node_list.append(initialization_expression_node)
    already_connected_node_list.append(condition_node)
    already_connected_node_list.append(loop_expression_node)
    # 设置禁止连接的节点
    ban_node_list.append(initialization_expression_node)
    ban_node_list.append(condition_node)


# 当遇到whileStatement的时候的解决方案
# 规则:
# 1.while_statement_node->condition_node
# 2.condition_node->block->第一句。
# 3.condition_node->外部第一句。
# 4.最后一句连接condition不需要写。
def while_statement_link_next_node(while_statement_node, stack, already_connected_node_list, ban_node_list):
    # 记录condition节点
    condition_node = None
    condition_node_node_id = while_statement_node.attribute['condition'][0]['id']
    condition_node_node_type = while_statement_node.attribute['condition'][0]['nodeType']
    block_node = None
    next_expression = None
    # 分别找出condition节点和block节点
    for node in while_statement_node.childes:
        node_id = node.node_id
        node_type = node.node_type
        if node_id == condition_node_node_id and node_type == condition_node_node_type:
            condition_node = node
        elif node_type == "Block":
            block_node = node
        else:
            next_expression = node
    # 1.while->condition
    while_statement_node.append_control_child(condition_node)
    # 2.condition->block第一句
    # 如果block不是空的，那就说明可能是只有一句话。
    if block_node is not None:
        next_expression = get_first_command_in_block(block_node)
    # 非空的时候可以进行连接
    if next_expression is not None:
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 3.condition->外部第一句
    next_expression = get_next_command_at_now(while_statement_node, ban_node_list)
    if next_expression is not None:
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 这两个节点的出度都已经设置完毕，不在更改。
    already_connected_node_list.append(while_statement_node)
    already_connected_node_list.append(condition_node)


# 当遇到了doWhile节点的时候处理的方法
# 规则:
# 1.doWhile直接连接block第一句
# 2.loop直接连回block第一句
# 3.loop直接连到外面的第一句
def do_while_statement_link_next_node(do_while_statement_node, stack, already_connected_node_list, ban_node_list):
    # 记录condition节点
    condition_node = None
    condition_node_node_id = do_while_statement_node.attribute['condition'][0]['id']
    condition_node_node_type = do_while_statement_node.attribute['condition'][0]['nodeType']
    # 记录block节点。
    block_node = None
    # 分别找出condition和block节点。
    for node in do_while_statement_node.childes:
        node_id = node.node_id
        node_type = node.node_type
        if node_id == condition_node_node_id and node_type == condition_node_node_type:
            condition_node = node
        elif node_type == "Block":
            block_node = node
    # 1.doWhile连接第一句body
    next_expression = get_first_command_in_block(block_node)
    if next_expression is not None:
        do_while_statement_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 2.loop连接block第一句。
    if next_expression is not None:
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 3.loop连接到外面的第一句
    next_expression = get_next_command_at_now(do_while_statement_node, ban_node_list)
    if next_expression is not None:
        condition_node.append_control_child(next_expression)
        stack.put(next_expression)
    # loop和doWhile都不再需要设置出度
    already_connected_node_list.append(do_while_statement_node)
    already_connected_node_list.append(condition_node)


# 如果是break的时候，使用的方法
# 规律:
# 1.先找到当前的节点是处于哪个循环控制中，最近的一个，一直往上递归就行。
# 2.根据获取的循环节点，可以直接获取下一句是谁，使用get_next_command_at_now方法
def break_link_next_node(break_node, stack, already_connected_node_list, ban_node_list):
    ancestor = break_node.parent
    # 只要不是这三个循环节点中的一个的时候，就继续往上找
    while ancestor.node_type not in ['ForStatement', 'WhileStatement', 'DoWhileStatement']:
        ancestor = ancestor.parent
    # 获取循环的下一句可以直接用来连接。
    next_expression = get_next_command_at_now(ancestor, ban_node_list)
    if next_expression is not None:
        break_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 已经不需要再设计出度了
    already_connected_node_list.append(break_node)


# 如果是continue的时候，使用的方法
# 规律：
# 1.先找到当前的节点是处于哪个循环控制中，最近的一个，一直往上递归就行。
# 2.如果是For循环，那continue需要连接到其中的loop
def continue_link_next_node(continue_node, stack, already_connected_node_list):
    ancestor = continue_node.parent
    # 只要不是这三个循环节点中的一个的时候，就继续往上找
    while ancestor.node_type not in ['ForStatement', 'WhileStatement', 'DoWhileStatement']:
        ancestor = ancestor.parent
    # 判断使用的是哪种循环
    if ancestor.node_type == "ForStatement":
        for_statement_node = ancestor
        # 从for_statement_node中找出以下的几部分信息，可以作为连接三个条件的判断条件。
        # 如果这个循环没有loop条件，有可能是None
        if for_statement_node.attribute['loopExpression'][0] is None:
            for child in for_statement_node.childes:
                if child.node_type == "virtue_node":
                    # 找到虚拟节点提示的下游边
                    next_expression = child.control_childes[0]
                    # 添加控制流边
                    continue_node.append_control_child(next_expression)
                    # 将下一个节点压入栈中，实际上是不需要的，因为肯定是已经处理过了。
                    stack.put(next_expression)
                    # 同时，当前的continue节点已经被处理过了，需要记录。
                    already_connected_node_list.append(continue_node)
                    # 只会有一个virtue_node，找到了就可以退出循环了。
                    break
        else:
            loop_expression_node = None
            loop_expression_node_node_id = for_statement_node.attribute['loopExpression'][0]['id']
            loop_expression_node_node_type = for_statement_node.attribute['loopExpression'][0]['nodeType']
            # 找出其中的loop节点。
            for node in for_statement_node.childes:
                node_id = node.node_id
                node_type = node.node_type
                # 说明当前找到的是loopExpression的节点。
                if node_id == loop_expression_node_node_id and node_type == loop_expression_node_node_type:
                    loop_expression_node = node
            # 设置next_expression为loop_expression_node
            next_expression = loop_expression_node
            # 添加控制流边
            continue_node.append_control_child(next_expression)
            # 将下一个节点压入栈中。
            stack.put(next_expression)
            # 同时，当前的continue节点已经被处理过了，需要记录。
            already_connected_node_list.append(continue_node)
    elif ancestor.node_type == "WhileStatement":
        while_statement_node = ancestor
        # 记录condition节点
        condition_node = None
        condition_node_node_id = while_statement_node.attribute['condition'][0]['id']
        condition_node_node_type = while_statement_node.attribute['condition'][0]['nodeType']
        # 分别找出condition节点
        for node in while_statement_node.childes:
            node_id = node.node_id
            node_type = node.node_type
            if node_id == condition_node_node_id and node_type == condition_node_node_type:
                condition_node = node
        # 设置next_expression为condition_node
        next_expression = condition_node
        # 添加控制流边
        continue_node.append_control_child(next_expression)
        # 将下一个节点压入栈中。
        stack.put(next_expression)
        # 同时，当前的continue节点已经被处理过了，需要记录。
        already_connected_node_list.append(continue_node)
    elif ancestor.node_type == "DoWhileStatement":
        do_while_statement_node = ancestor
        # 记录condition节点
        condition_node = None
        condition_node_node_id = do_while_statement_node.attribute['condition'][0]['id']
        condition_node_node_type = do_while_statement_node.attribute['condition'][0]['nodeType']
        # 分别找出condition和block节点。
        for node in do_while_statement_node.childes:
            node_id = node.node_id
            node_type = node.node_type
            if node_id == condition_node_node_id and node_type == condition_node_node_type:
                condition_node = node
        # 设置next_expression为condition_node
        next_expression = condition_node
        # 添加控制流边
        continue_node.append_control_child(next_expression)
        # 将下一个节点压入栈中。
        stack.put(next_expression)
        # 同时，当前的continue节点已经被处理过了，需要记录。
        already_connected_node_list.append(continue_node)


# 如果遇见了ModifierDefinition节点时的操作方法
# 规律:
# 1.直接找出其中的Block节点，取出第一句话，连上去。
def modifier_definition_node_link_next_node(modifier_definition_node, stack, already_connected_node_list):
    for node in modifier_definition_node.childes:
        if node.node_type == "Block":
            # 取出block中的第一句
            next_expression = get_first_command_in_block(node)
            # 添加ModifierDefinition节点和block第一句之间的控制流边
            modifier_definition_node.append_control_child(next_expression)
            # 压入栈
            stack.put(next_expression)
            # 设定为已经操作过了。
            already_connected_node_list.append(modifier_definition_node)
            break


# 当遇到了PlaceholderStatement的时候的操作方法
# 规则，直接找下一句进行连接
def placeholder_statement_link_next_node(placeholder_statement_node, stack, already_connected_node_list, ban_node_list):
    next_expression = get_next_command_at_now(placeholder_statement_node, ban_node_list)
    if next_expression is not None:
        placeholder_statement_node.append_control_child(next_expression)
        stack.put(next_expression)
    already_connected_node_list.append(placeholder_statement_node)


# 如果遇见了revertStatement节点，使用的方法
# 规则：
# 去找到整个图范围内部的ErrorDefinition节点
# 将revertStatement节点连接到ErrorDefinition节点上。
def revert_statement_link_next_node(revert_statement_node, stack, already_connected_node_list, project_node_dict):
    revert_call_error_id = revert_statement_node.attribute['errorCall'][0]['expression']['referencedDeclaration']
    for error in project_node_dict['ErrorDefinition']:
        error_id = error.node_id
        # 说明找到了对应的节点。
        if error_id == revert_call_error_id:
            # 将revertStatement和ErrorDefinition连接起来
            next_expression = error
            revert_statement_node.append_control_child(next_expression)
            stack.put(next_expression)
            already_connected_node_list.append(revert_statement_node)


# 关于return的处理方式
def return_link_next_node(return_node, already_connected_node_list):
    # return其实没有什么要连接的了。没有必要连接，除非是FunctionDefinition。
    link_function_call_list_at_now_now(return_node)
    already_connected_node_list.append(return_node)
