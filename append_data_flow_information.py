from queue import LifoQueue


# 给出所有的节点列表，为图上增加数据流信息
def append_data_flow_information(project_node_list, project_node_dict, file_name):
    # 1.首先找出构造函数以及预定义的内容，是为了和下面函数中的内容进行联动,注意是先执行预定义，再执行构造函数。
    pre_variable_node_list = []
    constructor_node = None
    for contract_node in project_node_dict['ContractDefinition']:
        for child_of_contract_node in contract_node.childes:
            # 是合约预先定义好的一些参数。
            if child_of_contract_node.node_type == "VariableDeclaration":
                pre_variable_node_list.append(child_of_contract_node)
            # 是合约的构造参数。
            if child_of_contract_node.node_type == "FunctionDefinition" and 'kind' in child_of_contract_node.attribute.keys() and child_of_contract_node.attribute['kind'][0] == "constructor":
                constructor_node = child_of_contract_node
    # 如果有构造函数的情况下，优先走掉构造函数，其他情况是没有优先级的。
    if constructor_node is not None:
        traverse_function_definition_node(constructor_node, pre_variable_node_list)
    # 不论构造函数是否已经完成操作，直接遍历别的函数定义节点。
    if "FunctionDefinition" in project_node_dict.keys():
        for function_definition_node in project_node_dict["FunctionDefinition"]:
            # 在调用完了traverse_function_definition_node的时候，会给functionDefinition节点打上属性，data_flow:True。未完成的则没有。
            if "data_flow" not in function_definition_node.attribute.keys():
                traverse_function_definition_node(function_definition_node, pre_variable_node_list)
    print(f"{file_name}节点数据流更新成功")


# 专门用来连接每一个FunctionDefinition节点下的数据流的。如果其中有涉及跨函数的部分，可以采用递归的手段。
def traverse_function_definition_node(function_definition_node, pre_variable_node):
    # 获取当前这个函数的参数和返回值。
    method_params, method_returns = get_method_message_at_function_definition_node(function_definition_node)
    # 开始模拟数据流，沿着控制流的方向走，应该使用深度遍历。
    stack = LifoQueue(maxsize=0)
    # 记录谁已经走过了，避免进入重复的死循环。
    already_gone_node_list = []
    # 将每一个控制流节点保存下来，保存的同时还要记录到这一行的时候可以使用哪些参数，返回值是谁。
    put_stack(function_definition_node, method_params, method_returns, stack)
    while not stack.empty():
        # 此时的pop_node是一个字典，包含了当前节点，当前可用的参数，当前函数的返回值。
        pop_node = stack.get()
        if pop_node in already_gone_node_list:
            continue
        # 如果不是一开始的函数定义节点不需要操作，后面自然会操作的。
        if pop_node is not function_definition_node:
            continue
        # 记录当前节点为已经走过的，避免重复
        already_gone_node_list.append(pop_node)
        if pop_node['node'].node_type in ["revert", "FunctionDefinition", "IfStatement", "ForStatement", "WhileStatement", "DoWhileStatement"]:
            for control_child in pop_node['node'].control_childes:
                put_stack(control_child, method_params, method_returns, stack)
        elif pop_node['node'].node_type == "VariableDeclarationStatement":
            variable_declaration_statement_data_flow(pop_node, method_params, method_returns, stack, pre_variable_node)
        elif pop_node['node'].node_type == "ExpressionStatement":
            expression_statement_data_flow(pop_node, method_params, method_returns, stack, pre_variable_node)
        elif pop_node['node'].node_type == "Return":
            return_data_flow(pop_node, method_params, method_returns, stack, pre_variable_node)
        elif pop_node['node'].node_type != "FunctionCall":
            for child in pop_node['node'].control_childes:
                put_stack(child, method_params, method_returns, stack)
    # 代表这个函数已经经过操作了，不需要重复操作。
    function_definition_node.attribute["data_flow"] = True


# 针对VariableDeclarationStatement节点的处理方法
def variable_declaration_statement_data_flow(variable_declaration_statement, method_param, method_return, stack, pre_variable_node):
    variable_declaration_statement_node = variable_declaration_statement['node']
    # 左边量的字典值
    declarations_dict = variable_declaration_statement_node.attribute['declarations'][0][0]
    target_node_id = declarations_dict['id']
    target_node_type = declarations_dict['nodeType']
    target_node_name = declarations_dict['name']
    target_node = None
    # 右边等式的内容字典
    if variable_declaration_statement_node.attribute['initialValue'][0] is not None:
        initial_value_dict = variable_declaration_statement_node.attribute['initialValue'][0]
        initial_node_id = initial_value_dict['id']
        initial_node_type = initial_value_dict['nodeType']
        initial_node = None
    else:
        initial_node_id = None
        initial_node_type = None
        initial_node = None
    # 先识别出这两个节点分别是谁。
    for child in variable_declaration_statement_node.childes:
        node_id = child.node_id
        node_type = child.node_type
        if node_id == target_node_id and node_type == target_node_type:
            target_node = child
        elif node_id == initial_node_id and node_type == initial_node_type:
            initial_node = child
    # 将target_node连接到之前出现的过参数上。
    link_pre_node(method_param, target_node, target_node_name, pre_variable_node)
    # 如果右半部分确实是存在的
    if initial_node:
        # 获取右半边的返回值是谁，并连接到target上。
        res = get_return(initial_node)
        res.append_data_child(target_node)
        # 将之前所有的点与这一批点相连接。
        res = get_all_literal_or_identifier_at_now(initial_node)
        for node in res:
            if "name" in node.attribute.keys():
                link_pre_node(method_param, node, node.attribute['name'], pre_variable_node)
    # 将当前的这个参数添加到method_param中
    method_param.append(target_node)
    # 压入控制流的后续节点。
    for control_child in variable_declaration_statement_node.control_childes:
        put_stack(control_child, method_param, method_return, stack)


# 根据子节点，找出他的返回节点是谁，但是并不需要继续连接，不过要和之前的参数进行连接。
def expression_statement_data_flow(pop_node, method_params, method_returns, stack, pre_variable_node):
    expression_statement_node = pop_node['node']
    # 传入普通节点
    for child_of_expression_statement_node in expression_statement_node.childes:
        # 并不需要和当前的expressionStatement节点相互连接，所以不需要返回值。
        get_return(child_of_expression_statement_node)
        # 这里需要找到当前下面所有可以连接的部分，然后与之前的参数相连接。
        res = get_all_literal_or_identifier_at_now(expression_statement_node)
        for node in res:
            if "name" in node.attribute.keys():
                link_pre_node(method_params, node, node.attribute['name'], pre_variable_node)
    # 为了继续深度遍历，所以需要传入控制流子节点。
    for child_of_expression_statement_node in expression_statement_node.control_childes:
        put_stack(child_of_expression_statement_node, method_params, method_returns, stack)


def return_data_flow(pop_node, method_params, method_returns, stack, pre_variable_node):
    return_node = pop_node['node']
    # 传入普通节点
    for child_of_return_node in return_node.childes:
        # 并不需要和当前的return节点相互连接，所以不需要返回值。
        get_return(child_of_return_node)
        # 这里需要找到当前下面所有可以连接的部分，然后与之前的参数相连接。
        res = get_all_literal_or_identifier_at_now(return_node)
        for node in res:
            if "name" in node.attribute.keys():
                link_pre_node(method_params, node, node.attribute['name'], pre_variable_node)
    # 如果没有子节点，那就根本不需要来连接，因为语句一定是return;
    if return_node.childes:
        # 找出所有在return中返回的组件,这种情况代表的是使用了多返回值。
        if "components" in return_node.attribute["expression"][0].keys():
            components = []
            # 获取这个子树下所有的内容，用来查询谁连接返回值使用。
            node_list = []
            stack = LifoQueue(maxsize=0)
            stack.put(return_node)
            node_list.append(return_node)
            while not stack.empty():
                pop_node = stack.get()
                for child in pop_node.childes:
                    node_list.append(child)
                    stack.put(child)
            for component_dict in return_node.attribute["expression"][0]["components"]:
                component_node_id = component_dict["id"]
                component_node_type = component_dict["nodeType"]
                for node in node_list:
                    if node.node_id == component_node_id and node.node_type == component_node_type:
                        components.append({"node": node, "node_id": component_node_id, "node_type": component_node_type})
            # 为每一个返回的元素添加到返回值上的边。
            for return_param, component in zip(method_returns, components):
                component["node"].append_data_child(return_param)
        else:
            expression_node_id = return_node.attribute["expression"][0]["id"]
            expression_node_type = return_node.attribute["expression"][0]["nodeType"]
            expression_node = None
            for node in return_node.childes:
                if node.node_id == expression_node_id and node.node_type == expression_node_type:
                    expression_node = node
            expression_node.append_data_child(method_returns[0])
    # 为了继续深度遍历，所以需要传入控制流子节点。
    for child_of_return_node in return_node.control_childes:
        put_stack(child_of_return_node, method_params, method_returns, stack)


# 将一个节点以及该节点所处位置对应的参数压入栈中。
def put_stack(node, method_param, method_return, stack):
    stack.put({"node": node, "param": method_param, "return": method_return})


# 查出在当前位置的子树中，有多少个可以连接的节点。
def get_all_literal_or_identifier_at_now(node):
    res = []
    stack = LifoQueue(maxsize=0)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        for child in pop_node.childes:
            stack.put(child)
        if pop_node.node_type in ["Literal", "Identifier"]:
            res.append(pop_node)
    return res


# 将当前的节点和之前出现过的变量进行连接。
def link_pre_node(method_params, target_node, target_node_name, pre_variable_node):
    flag = False
    # 先将左半部分来自哪里搞清楚，全部连起来。
    # 先从method_param中进行倒序遍历，以获取是来自于谁，如果没有找到，再去找pre_variable_node的问题。
    for node in method_params[::-1]:
        if node.attribute['name'] == target_node_name:
            # 从之前的参数连接到当前节点。
            node.append_data_child(target_node)
            flag = True
            break
    # 如果在之前的参数列表中还没有出现过，那说明使用的就是全局变量。
    if not flag:
        for node in pre_variable_node:
            node_name = node.attribute['name']
            if isinstance(node_name, list):
                node_name = node_name[0]
            if isinstance(target_node_name, list):
                target_node_name = target_node_name[0]
            if node_name == target_node_name:
                # 从之前的节点连接到当前的节点。
                node.append_data_child(target_node)
                break


# 找到一个FunctionDefinition节点下面的入参和出参。
def get_method_message_at_function_definition_node(function_definition_node):
    # 先取出这个节点的参数和返回值。
    method_params = []
    method_returns = []
    # 每一个FunctionDefinition节点下面都会有两个ParameterList，一般来说第一个就是参数节点，第二个是返回值节点。
    flag = 0
    for child in function_definition_node.childes:
        if child.node_type == "ParameterList":
            flag += 1
            # 遍历当前parameterList的子节点，找出其中的VariableDefinition
            for child_node_of_parameter_list in child.childes:
                # 代表是参数节点
                if child_node_of_parameter_list.node_type == "VariableDeclaration" and flag == 1:
                    method_params.append(child_node_of_parameter_list)
                # 代表是返回值节点
                if child_node_of_parameter_list.node_type == "VariableDeclaration" and flag == 2:
                    method_returns.append(child_node_of_parameter_list)
    return method_params, method_returns


# 获取以传入的节点为根的树的返回节点应该是谁。
def get_return(initial_node):
    if initial_node.node_type == "Identifier" or initial_node.node_type == "Literal" or "ElementaryTypeNameExpression":
        return initial_node
    need_recursion_types = ["Assignment", "BinaryOperation", "UnaryOperation", "FunctionCall", "TupleExpression", "IndexAccess", "MemberAccess", "Conditional"]
    # 如果是三目运算符，将两种结果连接到条件上，然后返回条件。
    if initial_node.node_type == "Conditional":
        conditional_node = initial_node
        # 获取三种节点的id和type
        condition_node_node_id = conditional_node.attribute["condition"][0]["id"]
        condition_node_node_type = conditional_node.attribute["condition"][0]["nodeType"]
        condition_node = None
        false_expression_node_id = conditional_node.attribute["falseExpression"][0]["id"]
        false_expression_node_type = conditional_node.attribute["falseExpression"][0]["nodeType"]
        false_expression_node = None
        true_expression_node_id = conditional_node.attribute["trueExpression"][0]["id"]
        true_expression_node_type = conditional_node.attribute["trueExpression"][0]["nodeType"]
        true_expression_node = None
        for child_of_conditional_node in conditional_node.childes:
            if child_of_conditional_node.node_type in need_recursion_types:
                if child_of_conditional_node.node_id == condition_node_node_id and child_of_conditional_node.node_type == condition_node_node_type:
                    condition_node = get_return(child_of_conditional_node)
                elif false_expression_node_id == condition_node_node_id and false_expression_node_type == condition_node_node_type:
                    false_expression_node = get_return(child_of_conditional_node)
                elif true_expression_node_id == condition_node_node_id and true_expression_node_type == condition_node_node_type:
                    true_expression_node = get_return(child_of_conditional_node)
            else:
                if child_of_conditional_node.node_id == condition_node_node_id and child_of_conditional_node.node_type == condition_node_node_type:
                    condition_node = child_of_conditional_node
                elif false_expression_node_id == condition_node_node_id and false_expression_node_type == condition_node_node_type:
                    false_expression_node = child_of_conditional_node
                elif true_expression_node_id == condition_node_node_id and true_expression_node_type == condition_node_node_type:
                    true_expression_node = child_of_conditional_node
        false_expression_node.append_data_child(condition_node)
        true_expression_node.append_data_child(condition_node)
        return condition_node
    # 如果是成员变量,只有一个子，直接获取子并返回。
    elif initial_node.node_type == "MemberAccess":
        member_access_node = initial_node
        return get_return(member_access_node.childes[0])
    # 如果是数组类型，下面的数组元素和下标元素都连接IndexAccess节点，然后返回IndexAccess
    elif initial_node.node_type == "IndexAccess":
        index_access_node = initial_node
        # 获取两个不需要递归计算的返回值，将两个返回值都连接都IndexAccess节点上，同时返回IndexAccess节点
        base_expression_node_node_id = index_access_node.attribute["baseExpression"][0]["id"]
        base_expression_node_node_type = index_access_node.attribute["baseExpression"][0]["nodeType"]
        base_expression_node = None
        index_expression_node_node_id = index_access_node.attribute["indexExpression"][0]["id"]
        index_expression_node_node_type = index_access_node.attribute["indexExpression"][0]["nodeType"]
        index_expression_node = None
        for child in index_access_node.childes:
            if child.node_type in need_recursion_types:
                if child.node_id == base_expression_node_node_id and child.node_type == base_expression_node_node_type:
                    base_expression_node = get_return(child)
                elif child.node_id == index_expression_node_node_id and child.node_type == index_expression_node_node_type:
                    index_expression_node = get_return(child)
            else:
                if child.node_id == base_expression_node_node_id and child.node_type == base_expression_node_node_type:
                    base_expression_node = child
                elif child.node_id == index_expression_node_node_id and child.node_type == index_expression_node_node_type:
                    index_expression_node = child
        base_expression_node.append_data_child(index_access_node)
        index_expression_node.append_data_child(index_access_node)
        return index_access_node
    # 如果是Tuple，其实可以忽略，但是依然需要向下移动。
    elif initial_node.node_type == "TupleExpression":
        tuple_expression_node = initial_node
        # 传入tuple的子节点，然后直接返回，这样就不会连接到tuple上。
        return get_return(tuple_expression_node.childes[0])
    # 如果是这种情况，需要获取两个不需要递归计算的返回值，将两个返回值连接到BinaryOperation节点上，同时返回BinaryOperation节点。
    elif initial_node.node_type == "BinaryOperation":
        binary_operation_node = initial_node
        res1 = None
        res2 = None
        # 搜索每一个子节点中可以直接连接Binary的节点
        for index, child_of_binary_operation_node in enumerate(binary_operation_node.childes):
            if child_of_binary_operation_node.node_type in need_recursion_types:
                if index == 0:
                    res1 = get_return(child_of_binary_operation_node)
                if index == 1:
                    res2 = get_return(child_of_binary_operation_node)
            else:
                if index == 0:
                    res1 = child_of_binary_operation_node
                if index == 1:
                    res2 = child_of_binary_operation_node
        # 将这两个返回值都连接到BinaryOperation节点上。
        res1.append_data_child(binary_operation_node)
        res2.append_data_child(binary_operation_node)
        # 同时返回自己。
        return binary_operation_node
    # 如果是UnaryOperation，需要获取一个返回节点，而且返回节点需要连接当前的unaryOperation节点，并返回UnaryOperation节点。
    elif initial_node.node_type == "UnaryOperation":
        unary_operation_node = initial_node
        res = get_return(unary_operation_node.childes[0])
        res.append_data_child(unary_operation_node)
        return unary_operation_node
    # 如果是Assignment节点，需要获取两个返回节点的时候，答案节点需要连接到结果节点上，然后返回结果节点。
    elif initial_node.node_type == "Assignment":
        assignment = initial_node
        res1 = None
        res2 = None
        # 搜索每一个子节点中可以直接连接Assignment的节点。
        for index, child_of_assignment in enumerate(assignment.childes):
            if child_of_assignment.node_type in need_recursion_types:
                if index == 0:
                    res1 = get_return(child_of_assignment)
                if index == 1:
                    res2 = get_return(child_of_assignment)
            else:
                if index == 0:
                    res1 = child_of_assignment
                if index == 1:
                    res2 = child_of_assignment
        # 将答案节点连接到结果节点上。
        res2.append_data_child(res1)
        return res2
    # 可以将所有的参数连接到Identifier上，因为这时候可以当作是函数，然后Identifier连接原始函数的输入，将输出连接到当前的Identifier节点上，然后再连接functionCall
    elif initial_node.node_type == "FunctionCall":
        function_call_node = initial_node
        arguments = []
        # 先取出所有的参数节点，作为一个列表
        for argument_child_node in function_call_node.attribute["arguments"][0]:
            argument_node_id = argument_child_node["id"]
            argument_node_type = argument_child_node["nodeType"]
            argument_node = None
            arguments.append({"node": argument_node, "node_id": argument_node_id, "node_type": argument_node_type})
        expression_node_node_id = function_call_node.attribute["expression"][0]["id"]
        expression_node_node_type = function_call_node.attribute["expression"][0]["nodeType"]
        expression_node = None
        # 遍历其中所有的子节点，分配角色。
        for child_of_function_call_node in function_call_node.childes:
            child_node_id = child_of_function_call_node.node_id
            child_node_type = child_of_function_call_node.node_type
            if child_node_id == expression_node_node_id and child_node_type == expression_node_node_type:
                expression_node = get_return(child_of_function_call_node)
            else:
                for argument in arguments:
                    if child_node_id == argument["node_id"] and child_node_type == argument["node_type"]:
                        argument["node"] = get_return(child_of_function_call_node)
        # 将所有的参数连接到对应的函数节点上。
        for argument in arguments:
            argument["node"].append_data_child(expression_node)
        # 找出FunctionCall的控制流子节点，判断其中是否含有FunctionDefinition节点，如果有，那就说明是内部函数调用，那么当前的expression_node需要连接到所有的入参上。
        for control_child in function_call_node.control_childes:
            if control_child.node_type == "FunctionDefinition":
                # 找出这个函数的入参。
                method_params, method_returns = get_method_message_at_function_definition_node(control_child)
                # 使用函数节点连接所有的入参
                for param in method_params:
                    expression_node.append_data_child(param)
                # 所有的出参连接函数。
                for return_param in method_returns:
                    return_param.append_data_child(expression_node)
        expression_node.append_data_child(function_call_node)
        # 直接返回这个函数信息节点作为返回值。
        return function_call_node
