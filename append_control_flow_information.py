from queue import LifoQueue
from bean.Node import Node


# 在工程文件夹内容全部读取完毕以后，传入生成的节点列表和节点字典，来为所有的节点添加控制流的边，此时的FunctionDefinition节点已经拥有了自己的method_name和params的参数。
# 第一趟：直接将所有的整句的句子先连接起来，因为Block中一定不会含有FunctionCall节点。
def append_control_flow_information(project_node_list, project_node_dict):
    # 设定待会进行遍历的容器。
    stack = LifoQueue(maxsize=0)
    # 记录哪些节点是已经连接好了的，不需要再发生变动的。
    already_connected_node_list = []
    # 禁止再被连接的节点列表
    ban_node_list = []
    # 代表在每一个FunctionDefinition节点中最后一句是谁，先不用管函数调用的情况，保存的格式是字典形式。{FunctionDefinitionNode: LastChildesNode}
    last_command_in_function_definition_node = {}
    # 从节点字典中取出所有的FunctionDefinition节点，对每一个FunctionDefinition节点进行操作。
    for function_definition_node in project_node_dict['FunctionDefinition']:
        # 先设定每一个函数的最后一句是自己，因为有的函数可能是空的函数体。
        last_command_in_function_definition_node[function_definition_node] = function_definition_node
        # 将这个FunctionDefinition节点压入栈中，作为遍历的根节点。
        stack.put(function_definition_node)
        # 如果栈不是空的，就一直进行遍历，因为当前函数还有内容没有被操作完。
        while not stack.empty():
            # 不断地从栈中取出内容进行下一步的连接操作，并将下一个节点重新压入到栈中。
            pop_node = stack.get()
            if pop_node in already_connected_node_list:
                continue
            # 根据节点的类型进行不同的操作，注意，这里永远不会出现虚拟节点，哪怕出现也没关系，因为不会有对应的操作。
            if pop_node.node_type == "FunctionDefinition":
                function_definition_type_link_next_node(pop_node, project_node_dict, stack, already_connected_node_list)
            elif pop_node.node_type == "IfStatement":
                if_statement_type_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
            elif pop_node.node_type == "ExpressionStatement":
                expression_statement_link_next_node(pop_node, stack, already_connected_node_list, ban_node_list)
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
    # 在所有的连接完成以后，删除所有的虚拟节点
    for for_statement_node in project_node_dict['ForStatement']:
        for index, node in enumerate(for_statement_node.childes):
            if node.node_type == "virtue_node":
                # 删除这个子节点
                del for_statement_node.childes[index]
                # 删除这个虚拟节点的下游边
                del node.control_childes[0]


# 找到block节点下面的第一句语句。
def get_first_command_in_block(block_node):
    next_expression = None
    # 忽略操作的几类节点。
    ignore_node_type_list = ['ParameterList', 'TryCatchClause', 'TryStatement', 'TupleExpression', 'UnaryOperation', 'UncheckedBlock', 'UserDefinedTypeName', 'UsingForDirective', 'VariableDeclaration', 'SourceUnit', 'StructDefinition', 'PragmaDirective', 'InlineAssembly', 'OverrideSpecifier', 'EnumDefinition', 'EnumValue', 'ElementaryTypeName', 'ElementaryTypeNameExpression', 'EmitStatement', 'PlaceholderStatement', 'EventDefinition', 'ArrayTypeName', 'Literal', 'Mapping', 'ContractDefinition']
    for child in block_node.childes:
        # 如果发现找到这个节点类型在忽略的类型当中
        if child.node_type in ignore_node_type_list:
            continue
        else:
            next_expression = child
            break
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
    if parent.node_type == "FunctionDefinition":
        return None
    #  如果父节点是If语句，那说明找下一句的时候肯定不会在if的子节点中找了
    if parent.node_type == "IfStatement":
        return get_next_command_at_now(parent, ban_node_list)
    # 返回的结果。
    next_expression = None
    # 忽略操作的几类节点。这里的最前的两种类型是为了避免for循环的最后一句话会连接到初始条件或者判断条件上。
    ignore_node_type_list = ['ParameterList', 'TryCatchClause', 'TryStatement', 'TupleExpression', 'UnaryOperation', 'UncheckedBlock', 'UserDefinedTypeName', 'UsingForDirective', 'VariableDeclaration', 'SourceUnit', 'StructDefinition', 'PragmaDirective', 'InlineAssembly', 'OverrideSpecifier', 'EnumDefinition', 'EnumValue', 'ElementaryTypeName', 'ElementaryTypeNameExpression', 'EmitStatement', 'PlaceholderStatement', 'EventDefinition', 'ArrayTypeName', 'Literal', 'Mapping', 'ContractDefinition']
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
    # if和block的数量
    if_statement_node_num = 0
    block_node_num = 0
    # 当找到这两类节点以后先保存一下，方便后面的操作。
    block_node_list = []
    if_statement_node_list = []
    binary_operation_node = None
    # 遍历其中所有的子节点，用来计算block子节点和if子节点有多少个。同时将节点的内容添加到数组中。
    for child_of_if_statement_node in if_statement_node.childes:
        if child_of_if_statement_node.node_type == "Block":
            block_node_num = block_node_num + 1
            block_node_list.append(child_of_if_statement_node)
        elif child_of_if_statement_node.node_type == "IfStatement":
            if_statement_node_num = if_statement_node_num + 1
            if_statement_node_list.append(child_of_if_statement_node)
        elif child_of_if_statement_node.node_type == "BinaryOperation":
            binary_operation_node = child_of_if_statement_node
            # if连上binary，后面用binary代替if连剩下的部分即可。
            if_statement_node.append_control_child(binary_operation_node)
    # 情况1:只有一个if
    if block_node_num == 1 and if_statement_node_num == 0:
        # 1.先做关于Block的工作,这就是那唯一的一个Block节点。
        block_node = block_node_list[0]
        # 设定好下一句是当前的Block的第一个子节点。
        next_expression = get_first_command_in_block(block_node)
        if next_expression is not None:
            binary_operation_node.append_control_child(next_expression)
            stack.put(next_expression)
        # 2.查询当前if语句的下一句
        next_expression = get_next_command_at_now(if_statement_node, ban_node_list)
        if next_expression is not None:
            binary_operation_node.append_control_child(next_expression)
            stack.put(next_expression)
    # if else 代表有两个block
    elif block_node_num == 2:
        # 分别获取两个block节点，然后获取两个block节点中的第一句
        block_node_1 = block_node_list[0]
        block_node_2 = block_node_list[1]
        # 找出Block1下面的第一句是谁，然后直接作为if的下一句连接。
        next_expression = get_first_command_in_block(block_node_1)
        if next_expression is not None:
            binary_operation_node.append_control_child(next_expression)
            stack.put(next_expression)
        # 找出Block2下面的第一句是谁，然后直接作为if的下一句连接。
        next_expression = get_first_command_in_block(block_node_2)
        if next_expression is not None:
            binary_operation_node.append_control_child(next_expression)
            stack.put(next_expression)
    # 如果两个都是1，说明是if else if...这样的
    elif block_node_num == 1 and if_statement_node_num == 1:
        # 获取其中的Block节点。
        block_node = block_node_list[0]
        # 找出Block下面的第一句，直接作为ifStatement的下一句。
        next_expression = get_first_command_in_block(block_node)
        if next_expression is not None:
            binary_operation_node.append_control_child(next_expression)
            stack.put(next_expression)
        # 获取其中的if节点
        next_expression = if_statement_node_list[0]
        # 这里获取的ifStatement一定不会空
        binary_operation_node.append_control_child(next_expression)
        stack.put(next_expression)
    # 这两个点的出度都已经配置完成，不需要进行新的操作。
    already_connected_node_list.append(if_statement_node)
    already_connected_node_list.append(binary_operation_node)


# 当遇到的结果是ExpressionStatement节点的时候使用的方法。
# 规则，直接去找下一句进行连接。
def expression_statement_link_next_node(expression_statement_node, stack, already_connected_node_list, ban_node_list):
    next_expression = get_next_command_at_now(expression_statement_node, ban_node_list)
    if next_expression is not None:
        expression_statement_node.append_control_child(next_expression)
        stack.put(next_expression)
    already_connected_node_list.append(expression_statement_node)


# 当遇到了VariableDeclarationStatement节点的时候使用的方法。
# 规则，直接找出当前句子的下一句进行连接。
def variable_declaration_statement_link_next_node(variable_declaration_statement_node, stack, already_connected_node_list, ban_node_list):
    next_expression = get_next_command_at_now(variable_declaration_statement_node, ban_node_list)
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
    if for_statement_node.attribute['initializationExpression'][0] is None:
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
    if for_statement_node.attribute['loopExpression'][0] is None:
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
    if for_statement_node.attribute['condition'][0] is None:
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
    # 下面不管节点是否存在，因为创建了虚拟节点进行代替，所以可以直接使用。
    # 1.连接for循环和第一句初始化句子
    for_statement_node.append_control_child(initialization_expression_node)
    # 2.连接第一句初始化句子和判断语句。
    initialization_expression_node.append_control_child(condition_node)
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
    # 分别找出condition节点和block节点
    for node in while_statement_node.childes:
        node_id = node.node_id
        node_type = node.node_type
        if node_id == condition_node_node_id and node_type == condition_node_node_type:
            condition_node = node
        elif node_type == "Block":
            block_node = node
    # 1.while->condition
    while_statement_node.append_control_child(condition_node)
    # 2.condition->block第一句
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


# 当遇到了dowhile节点的时候处理的方法
# 规则:
# 1.dowhile直接连接block第一句
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
    # 1.dowhile连接第一句body
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
