from queue import LifoQueue
import config


# 判断文件中是否含有重入的漏洞。
def make_reentry_attack_label(project_node_dict, file_name):
    # 如果是generate_all，并不需要继续操作，因为这时候在create_corpus_txt的时候已经生成过标签了。
    if config.create_corpus_mode == "generate_all":
        return
    # 默认没有重入攻击，只有当发现了重入攻击的时候，才会修改标签
    reentry_flag = False
    # 遍历当前合约中的ContractDefinition节点，因为获取预定义参数的时候对于不同的ContractDefinition节点来说是不一样的。
    for contract_node in project_node_dict['ContractDefinition']:
        # 如果在某一次循环中已经发现当前文件中是带有漏洞的，那就直接可以直接退出循环得出答案了。
        if reentry_flag:
            break
        # 代表合约中预定义的参数，后面进行控制流回溯的时候会用到。
        pre_variable_node_list = []
        # 遍历ContractDefinition节点下面的子节点，这些子节点就是预定义参数的节点。
        for child_of_contract_node in contract_node.childes:
            # 当类型是VariableDeclaration的时候，才是参数预定义，注意，在这个位置不管有没有等号赋值都只会是VariableDeclaration。
            if child_of_contract_node.node_type == "VariableDeclaration":
                # 将当前这个变量的节点添加到数组中。
                pre_variable_node_list.append(child_of_contract_node)
        # 遍历合约当中的函数定义节点，对每一个函数分开来进行判断。
        for function_definition_node in project_node_dict["FunctionDefinition"]:
            # 必须是在当前遍历的合约下，才能进行漏洞检测。
            if function_definition_node.parent == contract_node and len(function_definition_node.control_childes):
                # 记录回溯的操作结果的
                has_reentry_flag = []
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
                traverse_reentry_attack(project_node_dict, function_definition_node, method_params, now_node, [], has_reentry_flag)
                if len(has_reentry_flag):
                    reentry_flag = True
                    break
    print(f"{file_name}重入标签已经打上了。")
    # 最终返回这个控制的变量即可。
    if reentry_flag:
        return 1
    else:
        return 0


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


# 判断节点node，是不是functionDefinition节点的子节点，True代表是，False代表不是。
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


# 判断任意节点的修饰符中是否含有onlyOwner,如果含有就返回True
def have_only_owner_modifiers(arbitrarily_node):
    function_definition_node = arbitrarily_node
    while function_definition_node.node_type != "FunctionDefinition":
        function_definition_node = function_definition_node.parent
    if len(function_definition_node.attribute["modifiers"][0]):
        modifier_list = function_definition_node.attribute["modifiers"][0]
        for modifier in modifier_list:
            if "name" in modifier.keys() and modifier["name"] == "onlyOwner":
                return True
            if "modifierName" in modifier.keys() and modifier["modifierName"]["name"] == "onlyOwner":
                return True
    return False


# 进行回溯+控制流遍历所有的控制流路线
# project_node_dict:暂时还没有用处，先放着。
# function_definition_node:函数定义节点，到时候可以判断是不是走到了另外的函数定义节点的域中。
# params:到当前位置的时候,已经被记录的参数
# now_node:当前的节点位置
# path:记录所有走过的节点,以避免进行死循环
# is_overlap:是否重叠了。
def traverse_reentry_attack(project_node_dict, function_definition_node, params, now_node, path, has_reentry_flag):
    # 如果当前节点不是属于当前的函数定义节点的子节点,结束当前路径。
    if is_child_of_function_definition_node(now_node, function_definition_node) is False:
        return
    # 计数器：记录当前这个节点已经在路径中出现了几次，当出现了两次及以上的时候，说明陷入了死循环，直接退出。
    count = 0
    # 遍历所有的已经路过的节点，如果当前节点出现了，那就增加计数器
    for gone_node in path:
        if now_node == gone_node:
            count += 1
    # 如果这个节点已经走过两次了，那也结束当前路径，因为这代表进入了死循环之类的。
    if count >= 2:
        return
    # 从这里开始代表当前节点是可以走的,所以,先取出所有的参数,添加到params当中.
    all_could_connect_param = get_all_literal_or_identifier_at_now(now_node)
    # 记录当前这个节点有多少个参数被添加到了params中。
    effective_push_count = 0
    for param in all_could_connect_param:
        # 避免重复加入
        if param not in params:
            effective_push_count += 1
            params.append(param)
    # 进行回溯操作
    for control_child in now_node.control_childes:
        # 如果是走回去了，那就是形成环了，直接跳过。
        if control_child == now_node.parent:
            continue
        # 说明已经找到漏洞了，不再进行深一步的循环
        if len(has_reentry_flag) != 0:
            continue
        # 对当前的状态进行重入标签函数的判断,如果返回值是True，那说明是有漏洞的，直接往列表中新增加一个标记
        if reentry_attack(params, now_node) is True:
            has_reentry_flag.append(True)
            continue
        path.append(now_node)
        # 进一步的进行检测
        traverse_reentry_attack(project_node_dict, function_definition_node, params, control_child, path, has_reentry_flag)
        path.pop(-1)
    # 回溯完了以后,需要将内容删除掉,以实现状态的回退.
    for _ in range(effective_push_count):
        params.pop(-1)


# 判断是不是等号的左端。
def is_assignment_left(node):
    parent = node.parent
    # 除非空或者是等号的时候才会停下来
    while parent is not None and parent.node_type != "Assignment":
        parent = parent.parent
    # 如果不是空，那就说明是等号
    if parent is not None:
        if node == parent.childes[0]:
            return True
    return False


# 检验IndexAccess是否含有一样的结构，而且源代码是一样的。
def has_same_structure(argument_node, node):
    tmp1 = []
    tmp2 = []
    stack = LifoQueue()
    stack.put(argument_node)
    while not stack.empty():
        pop_node = stack.get()
        tmp1.append(pop_node)
        for child in pop_node.childes:
            stack.put(child)
    stack.put(node)
    while not stack.empty():
        pop_node = stack.get()
        tmp2.append(pop_node)
        for child in pop_node.childes:
            stack.put(child)
    if len(tmp1) == len(tmp2):
        for tmp in zip(tmp1, tmp2):
            if tmp[0].node_type == tmp[1].node_type and tmp[0].attribute["src_code"] == tmp[1].attribute["src_code"]:
                continue
            else:
                return False
    return True


# 当走到了now_node的时候，进行重入漏洞的判断
def reentry_attack(params, now_node):
    # 当前节点需要是FunctionCall节点，拥有memberName属性，且memberName属性是value才能判断是call.value这个函数。
    if now_node.node_type == "FunctionCall" and "memberName" in now_node.attribute["expression"][0].keys() and now_node.attribute["expression"][0]["memberName"] == "value":
        # call.value调用的参数的节点id和节点类型
        argument_node_node_id = now_node.attribute["arguments"][0][0]["id"]
        argument_node_node_type = now_node.attribute["arguments"][0][0]["nodeType"]
        argument_node = None
        # 根据参数的详细信息取到对应的参数节点。
        for child_of_function_call_node in now_node.childes:
            # 如果节点id和节点类型都可以对的上, 那当前节点就是call.value使用的参数节点.
            if child_of_function_call_node.node_id == argument_node_node_id and child_of_function_call_node.node_type == argument_node_node_type:
                # 记录转账使用的参数节点.
                argument_node = child_of_function_call_node
        # 记录已经被使用过的转账的参数节点，因为后面可能会涉及等价的判断，导致多种节点都可以作为转账节点。
        use_argument_node_list = []
        # 只要转账的参数节点不是空，就一直循环。
        while argument_node is not None:
            # 记录一次转账的节点，避免下一次重复使用该节点
            use_argument_node_list.append(argument_node)
            # 如果源代码的内容是0或者拥有修饰符,那就说明不可能会有问题,直接返回False，但是修饰符暂不明确可不可以，先留着注释掉。
            # if have_only_owner_modifiers(now_node):
            #     return False
            if argument_node.attribute["src_code"] == "0":
                return False
            # 如果参数是常数,按照常数的方式进行判断
            if argument_node.node_type == "Literal":
                # 遍历所有在当前的控制流之前出现过的参数节点,看看其中是否有过进行余额变动的内容.
                for other_literal_node in params[::-1]:
                    # 首先要满足的条件是节点的类型是Literal,而且other_literal_node的字面量和argument_node的字面量是相同的,并且两个不是同一个节点
                    if other_literal_node.node_type == "Literal" and other_literal_node.attribute["src_code"] == argument_node.attribute["src_code"] and other_literal_node != argument_node:
                        # 该常量的父节点，后续用来判断是不是等式。
                        other_literal_node_parent = other_literal_node.parent
                        # 如果是等式，而且用了-=号。如果是二元操作符，使用了-号。都是符合条件的。
                        if (other_literal_node_parent.node_type == "Assignment" and other_literal_node_parent.attribute["operator"][0] == "-=") or (other_literal_node_parent.node_type == "BinaryOperation" and other_literal_node_parent.attribute["operator"][0] == "-"):
                            # 再继续判断该符号的减量是不是找到的这个字面量，如果是，那就大功告成，说明成功找到了减少余额的地方。
                            if other_literal_node_parent.childes[1] == other_literal_node:
                                return False
                # 经过了一论循环，发现没有余额直接使用字面量进行变动，所以开始找等价情况。
                # 记录是否由等价的元素
                have_equal_variable = False
                # 遍历所有的参数节点,注意逆序查询.
                for param in params[::-1]:
                    # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                    if have_equal_variable:
                        break
                    # 使用了Literal作为Assignment第二个子节点的部分，而且该字面量需要和转账金额一样大,而且和原始的argument节点不是同一个节点。
                    if param.node_type == "Literal" and param.parent.node_type == "Assignment" and param == param.parent.childes[1] and param.attribute["src_code"] == argument_node.attribute["src_code"] and param != argument_node:
                        # 可以直接得出起点
                        start_node = param.parent.childes[0]
                        # 如果已经被使用过了,那就不要再次使用了.
                        if start_node in use_argument_node_list:
                            continue
                        # 根据起点我们可以推断出最后一次使用这个变量的位置,将这个推断出的位置,再一次当作新的转账金额进行判断即可.
                        for last_appear_position in params[::-1]:
                            # 如果遍历的节点确实是起点的后续数据流，而且该节点不是等式左端
                            if last_appear_position in start_node.data_childes and is_assignment_left(last_appear_position) is False:
                                argument_node = last_appear_position
                                have_equal_variable = True
                                break
                # 如果没有等价的元素,设定argument_node为None,即可退出循环
                if have_equal_variable is False:
                    argument_node = None
            # 如果是一个简单的变量
            elif argument_node.node_type == "Identifier":
                # 先取出余额节点
                identifier_node = argument_node
                # 先获取变量的来源,注意这里会是一个数组,需要和param取交集,取交集也是有说法的,需要在param中进行倒序遍历,第一个出现在列表中的就是来源.这里面的都有可能是变量的来源，所以需要倒序变量params。
                origin_node_list = identifier_node.data_parents
                origin_node = None
                # 进行倒序遍历,查询哪一个变量,第一次在原始节点的列表中出现了.
                for param in params[::-1]:
                    if param in origin_node_list:
                        origin_node = param
                # 连源头都没找到，那就更不可能有余额变化的地方
                if origin_node is None:
                    return True
                # 遍历来源节点的所有的数据流子节点,这些地方用的都是和转账的变量一样的,还没有被修改过,所以只要检查字面量即可.
                for data_child_of_origin_node in origin_node.data_childes:
                    # 如果当前这个数据流子节点是在等号左端的，那就是被赋值的对象，没有什么意义，跳过操作。
                    if is_assignment_left(data_child_of_origin_node) is True:
                        continue
                    # 判断是不是在param中，因为params中的才是已经都出现过的。
                    if data_child_of_origin_node not in params:
                        continue
                    # 取出父节点,是为了判断父节点是不是BinaryOperation或者Assignment节点.然后判断是不是被用来修改了余额.而且child_of_origin_node一定要作为第二个子元素出现。
                    parent = data_child_of_origin_node.parent
                    if len(parent.childes) == 2 and data_child_of_origin_node == parent.childes[1]:
                        if (parent.node_type == "Assignment" and parent.attribute["operator"][0] == "-=") or (parent.node_type == "BinaryOperation" and parent.attribute["operator"][0] == "-"):
                            return False
                # 经过对argument的查询，发现不存在，那就要找对应的等价节点。
                # 记录是否由等价的元素
                have_equal_variable = False
                # 遍历所有的参数节点,注意逆序查询.
                for find_assignment_param in params[::-1]:
                    # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                    if have_equal_variable:
                        break
                    # 只对等式处理
                    if find_assignment_param.parent.node_type == "Assignment":
                        # argument_node在Assignment的子节点中,而且argument_node是另外一个子节点的数据流子节点
                        # 这里是转账金额 = tmp，tmp更新转账金额
                        if argument_node == find_assignment_param.parent.childes[0] and argument_node in find_assignment_param.parent.childes[1].data_childes:
                            # 遍历由param.parent.childes[1]得出对应的data_parents
                            for source_node_of_tmp_variable in params[::-1]:
                                # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                                if have_equal_variable:
                                    break
                                # 符合条件的节点，说明是tmp变量的来源。
                                if source_node_of_tmp_variable in find_assignment_param.parent.childes[1].data_parents:
                                    # 可以直接得出起点
                                    assignment_left_node = source_node_of_tmp_variable
                                    # 如果已经被使用过了,那就不要再次使用了.
                                    if assignment_left_node in use_argument_node_list:
                                        continue
                                    for last_appear_position in params[::-1]:
                                        if last_appear_position in assignment_left_node.data_childes:
                                            argument_node = last_appear_position
                                            have_equal_variable = True
                                            break
                        elif argument_node == find_assignment_param.parent.childes[1] and argument_node in find_assignment_param.parent.childes[0].data_childes:
                            # 可以直接得出起点
                            assignment_left_node = find_assignment_param.parent.childes[1]
                            # 如果已经被使用过了,那就不要再次使用了.
                            if assignment_left_node in use_argument_node_list:
                                continue
                            for last_appear_position in params[::-1]:
                                if last_appear_position in assignment_left_node.data_childes:
                                    argument_node = last_appear_position
                                    have_equal_variable = True
                                    break
                # 如果没有等价的元素,设定argument_node为None,即可退出循环
                if have_equal_variable is False:
                    argument_node = None
            elif argument_node.node_type == "IndexAccess":
                # 遍历所有在当前的控制流之前出现过的参数节点,看看其中是否有过进行余额变动的内容.
                for other_index_access_node in params[::-1]:
                    # 首先要满足的条件是，一定得是IndexAccess。然后就是拥有一样的结构。
                    if other_index_access_node.node_type == "IndexAccess" and has_same_structure(argument_node, other_index_access_node):
                        # 该数组索引元素的父节点，后续用来判断是不是等式。
                        other_index_access_node_parent = other_index_access_node.parent
                        # 如果是等式，而且用了-=号。如果是二元操作符，使用了-号。都是符合条件的。
                        if (other_index_access_node_parent.node_type == "Assignment" and other_index_access_node_parent.attribute["operator"][0] == "-=") or (other_index_access_node_parent.node_type == "BinaryOperation" and other_index_access_node_parent.attribute["operator"][0] == "-"):
                            # 再继续判断该符号的减量是不是找到的这个IndexAccess，如果是，那就大功告成，说明成功找到了减少余额的地方。
                            if other_index_access_node_parent.childes[1] == other_index_access_node:
                                return False
                # 经过了一论循环，发现没有余额直接使用IndexAccess进行变动，所以开始找等价情况。
                # 记录是否有等价的元素
                have_equal_variable = False
                # 遍历所有的参数节点,注意逆序查询.
                for param in params[::-1]:
                    # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                    if have_equal_variable:
                        break
                    # 使用了IndexAccess作为Assignment中的第二个子节点,而且该第二个子节点和argument_node拥有一样的结构。
                    if param.node_type == "IndexAccess" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[1]:
                        # 可以直接得出起点
                        start_node = param.parent.childes[0]
                        # 如果已经被使用过了,那就不要再次使用了.
                        if start_node in use_argument_node_list:
                            continue
                        # 根据起点我们可以推断出最后一次使用这个变量的位置,将这个推断出的位置,再一次当作新的转账金额进行判断即可.
                        for last_appear_position in params[::-1]:
                            # 如果遍历的节点确实是起点的后续数据流，而且该节点不是等式左端
                            if last_appear_position in start_node.data_childes and is_assignment_left(last_appear_position) is False:
                                argument_node = last_appear_position
                                have_equal_variable = True
                                break
                    # 当结果被作为了第一个子节点的时候的处理方式,也就是金额 = tmp
                    elif param.node_type == "IndexAccess" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[0]:
                        # 遍历由param.parent.childes[1]得出对应的data_parents
                        for source_node_of_tmp_variable in params[::-1]:
                            # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                            if have_equal_variable:
                                break
                            # 符合条件的节点，说明是tmp变量的来源。
                            if source_node_of_tmp_variable in param.data_parents:
                                # 可以直接得出起点
                                assignment_left_node = source_node_of_tmp_variable
                                # 如果已经被使用过了,那就不要再次使用了.
                                if assignment_left_node in use_argument_node_list:
                                    continue
                                for last_appear_position in params[::-1]:
                                    if last_appear_position in assignment_left_node.data_childes:
                                        argument_node = last_appear_position
                                        have_equal_variable = True
                                        break
                # 如果没有等价的元素,设定argument_node为None,即可退出循环
                if have_equal_variable is False:
                    argument_node = None
            elif argument_node.node_type == "BinaryOperation":
                # 遍历所有在当前的控制流之前出现过的参数节点,看看其中是否有过进行余额变动的内容.
                for other_binary_operation_node in params[::-1]:
                    # 首先要满足的条件是，一定得是BinaryOperation。然后就是拥有一样的结构。
                    if other_binary_operation_node.node_type == "BinaryOperation" and has_same_structure(argument_node, other_binary_operation_node):
                        # 该数组索引元素的父节点，后续用来判断是不是等式。
                        other_binary_operation_node_parent = other_binary_operation_node.parent
                        # 如果是等式，而且用了-=号。如果是二元操作符，使用了-号。都是符合条件的。
                        if (other_binary_operation_node_parent.node_type == "Assignment" and other_binary_operation_node_parent.attribute["operator"][0] == "-=") or (other_binary_operation_node_parent.node_type == "BinaryOperation" and other_binary_operation_node_parent.attribute["operator"][0] == "-"):
                            # 再继续判断该符号的减量是不是找到的这个BinaryOperation，如果是，那就大功告成，说明成功找到了减少余额的地方。
                            if other_binary_operation_node_parent.childes[1] == other_binary_operation_node:
                                return False
                # 经过了一论循环，发现没有余额直接使用BinaryOperation进行变动，所以开始找等价情况。
                # 记录是否有等价的元素
                have_equal_variable = False
                # 遍历所有的参数节点,注意逆序查询.
                for param in params[::-1]:
                    # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                    if have_equal_variable:
                        break
                    # 使用了BinaryOperation作为Assignment中的第二个子节点,而且该第二个子节点和argument_node拥有一样的结构。
                    if param.node_type == "BinaryOperation" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[1]:
                        # 可以直接得出起点
                        start_node = param.parent.childes[0]
                        # 如果已经被使用过了,那就不要再次使用了.
                        if start_node in use_argument_node_list:
                            continue
                        # 根据起点我们可以推断出最后一次使用这个变量的位置,将这个推断出的位置,再一次当作新的转账金额进行判断即可.
                        for last_appear_position in params[::-1]:
                            # 如果遍历的节点确实是起点的后续数据流，而且该节点不是等式左端
                            if last_appear_position in start_node.data_childes and is_assignment_left(last_appear_position) is False:
                                argument_node = last_appear_position
                                have_equal_variable = True
                                break
                    # 当结果被作为了第一个子节点的时候的处理方式,也就是金额 = tmp
                    elif param.node_type == "BinaryOperation" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[0]:
                        # 遍历由param.parent.childes[1]得出对应的data_parents
                        for source_node_of_tmp_variable in params[::-1]:
                            # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                            if have_equal_variable:
                                break
                            # 符合条件的节点，说明是tmp变量的来源。
                            if source_node_of_tmp_variable in param.data_parents:
                                # 可以直接得出起点
                                assignment_left_node = source_node_of_tmp_variable
                                # 如果已经被使用过了,那就不要再次使用了.
                                if assignment_left_node in use_argument_node_list:
                                    continue
                                for last_appear_position in params[::-1]:
                                    if last_appear_position in assignment_left_node.data_childes:
                                        argument_node = last_appear_position
                                        have_equal_variable = True
                                        break
                # 如果没有等价的元素,设定argument_node为None,即可退出循环
                if have_equal_variable is False:
                    argument_node = None
            elif argument_node.node_type == "MemberAccess":
                # 遍历所有在当前的控制流之前出现过的参数节点,看看其中是否有过进行余额变动的内容.
                for other_member_access_node in params[::-1]:
                    # 首先要满足的条件是，一定得是MemberAccess。然后就是拥有一样的结构。
                    if other_member_access_node.node_type == "MemberAccess" and has_same_structure(argument_node, other_member_access_node):
                        # 该数组索引元素的父节点，后续用来判断是不是等式。
                        other_member_access_node_parent = other_member_access_node.parent
                        # 如果是等式，而且用了-=号。如果是二元操作符，使用了-号。都是符合条件的。
                        if (other_member_access_node_parent.node_type == "Assignment" and other_member_access_node_parent.attribute["operator"][0] == "-=") or (other_member_access_node_parent.node_type == "BinaryOperation" and other_member_access_node_parent.attribute["operator"][0] == "-"):
                            # 再继续判断该符号的减量是不是找到的这个MemberAccess，如果是，那就大功告成，说明成功找到了减少余额的地方。
                            if other_member_access_node_parent.childes[1] == other_member_access_node:
                                return False
                # 经过了一论循环，发现没有余额直接使用MemberAccess进行变动，所以开始找等价情况。
                # 记录是否有等价的元素
                have_equal_variable = False
                # 遍历所有的参数节点,注意逆序查询.
                for param in params[::-1]:
                    # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                    if have_equal_variable:
                        break
                    # 使用了MemberAccess作为Assignment中的第二个子节点,而且该第二个子节点和argument_node拥有一样的结构。
                    if param.node_type == "MemberAccess" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[1]:
                        # 可以直接得出起点
                        start_node = param.parent.childes[0]
                        # 如果已经被使用过了,那就不要再次使用了.
                        if start_node in use_argument_node_list:
                            continue
                        # 根据起点我们可以推断出最后一次使用这个变量的位置,将这个推断出的位置,再一次当作新的转账金额进行判断即可.
                        for last_appear_position in params[::-1]:
                            # 如果遍历的节点确实是起点的后续数据流，而且该节点不是等式左端
                            if last_appear_position in start_node.data_childes and is_assignment_left(last_appear_position) is False:
                                argument_node = last_appear_position
                                have_equal_variable = True
                                break
                    # 当结果被作为了第一个子节点的时候的处理方式,也就是金额 = tmp
                    elif param.node_type == "MemberAccess" and param.parent.node_type == "Assignment" and has_same_structure(argument_node, param) and param == param.parent.childes[0]:
                        # 遍历由param.parent.childes[1]得出对应的data_parents
                        for source_node_of_tmp_variable in params[::-1]:
                            # 如果已经找到了等价元素，那就跳出循环，没有必要继续了
                            if have_equal_variable:
                                break
                            # 符合条件的节点，说明是tmp变量的来源。
                            if source_node_of_tmp_variable in param.data_parents:
                                # 可以直接得出起点
                                assignment_left_node = source_node_of_tmp_variable
                                # 如果已经被使用过了,那就不要再次使用了.
                                if assignment_left_node in use_argument_node_list:
                                    continue
                                for last_appear_position in params[::-1]:
                                    if last_appear_position in assignment_left_node.data_childes:
                                        argument_node = last_appear_position
                                        have_equal_variable = True
                                        break
                # 如果没有等价的元素,设定argument_node为None,即可退出循环
                if have_equal_variable is False:
                    argument_node = None
        # 如果是这种函数，而且没有找到合适的语句，那就返回True
        return True
    # 都不是函数调用，肯定是没有问题的.
    return False
