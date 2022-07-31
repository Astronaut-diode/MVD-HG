from queue import LifoQueue
from bean.Node import Node


# 为当前的项目图结构，增加数据流信息
def append_data_flow_information(project_node_list, project_node_dict, file_name):
    # 找出构造函数以及预定义的内容，是为了和下面函数中的内容进行联动.
    pre_variable_node_list = []
    # 遍历所有的ContractDefinition节点，因为一个文件中可能含有多个合约。
    for contract_node in project_node_dict['ContractDefinition']:
        # 为当前的合约增加几个新的节点,即默认属性,比如说this,msg.
        # 记得要增加抽线语法树的关系避免成为孤岛.并记录下当前的节点
        max = 0
        for loop in project_node_list:
            if loop.node_id >= max:
                max = loop.node_id
        msg_node = Node(max + 1, "VariableDeclaration", contract_node)
        msg_node.append_attribute("name", "msg")
        msg_node.append_attribute("src_code", "")
        contract_node.append_child(msg_node)
        project_node_list.append(msg_node)
        project_node_dict["VariableDeclaration"].append(msg_node)
        this_node = Node(max + 2, "VariableDeclaration", contract_node)
        this_node.append_attribute("name", "this")
        this_node.append_attribute("src_code", "")
        contract_node.append_child(this_node)
        project_node_list.append(this_node)
        project_node_dict["VariableDeclaration"].append(this_node)
        # 遍历ContractDefinition节点下面的子节点，这些子节点就是预定义参数的节点。
        for child_of_contract_node in contract_node.childes:
            # 当类型是VariableDeclaration的时候，才是参数预定义，注意，在这个位置不管有没有等号赋值都只会是VariableDeclaration。
            if child_of_contract_node.node_type == "VariableDeclaration":
                # 将当前这个变量的节点添加到数组中。
                pre_variable_node_list.append(child_of_contract_node)
        # 如果当前的合约中是含有FunctionDefinition类型的。
        if "FunctionDefinition" in project_node_dict.keys():
            # 遍历所有的FunctionDefinition节点。
            for function_definition_node in project_node_dict["FunctionDefinition"]:
                # 在调用完了traverse_function_definition_node的时候，会给functionDefinition节点打上属性，data_flow:True。未完成的则没有。还要满足在同一个合约中的条件。
                if "data_flow" not in function_definition_node.attribute.keys() and function_definition_node.parent == contract_node:
                    # 根据函数定义节点获取他的函数入参和出参。
                    method_params, method_returns = get_method_message_at_function_definition_node(function_definition_node)
                    # 回溯+控制流的方法从function_definition_node出发去遍历整个轨迹，做到每一个控制流都有数据流
                    traverse_function_definition_node(function_definition_node, function_definition_node, pre_variable_node_list, method_params, method_returns, [])
    print(f"{file_name}节点数据流更新成功")


# 找到一个FunctionDefinition节点下面的入参和出参
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


# 判断节点node，是不是functionDefinition节点的子节点。
def is_child_of_function_definition_node(node, function_definition_node):
    # 先设定parent，然后不断的往上迭代,判断是不是合理的函数定义节点的效果范围内。
    parent = node
    while parent is not None:
        if parent is function_definition_node:
            return True
        else:
            parent = parent.parent
    return False


# 从函数定义节点开始遍历控制流，注意这里使用的是回溯+控制流的方法。
# function_definition_node:代表当前处理的函数是谁，可以用来判断回溯是否越界了。
# now_node:当前已经走到哪个节点了。
# pre_variable_node_list:预定义的参数列表。
# method_params:是代表原始函数的入参，是一个一维数组
# method_returns:代表原始函数的出参，是一个一维数组
# path:当前这条路线经过的一些位置,是一个一维数组。
def traverse_function_definition_node(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    # 如果当前节点不是属于当前的函数定义节点的子节点,结束当前路径。
    if is_child_of_function_definition_node(now_node, function_definition_node) is False:
        return
    count = 0
    # 遍历所有的已经路过的节点，如果当前节点出现了，那就增加计数器
    for gone_node in path:
        if now_node == gone_node:
            count += 1
    # 如果这个节点已经走过两次了，那也结束当前路径，因为这代表进入了死循环之类的。
    if count >= 2:
        return
    # 从这里开始，代表当前这个节点是可以走的，所以先操作now_node的节点信息。
    # 如果节点类型是["revert", "FunctionDefinition", "IfStatement", "ForStatement", "WhileStatement", "DoWhileStatement"]中的某一种，其实没有处理的必要，只是简单的当作分岔路的路口即可。
    if now_node.node_type in ["revert", "FunctionDefinition", "IfStatement", "ForStatement", "WhileStatement", "DoWhileStatement"]:
        processing_control_flow_forks(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    elif now_node.node_type == "VariableDeclarationStatement":
        processing_variable_declaration_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    elif now_node.node_type in ["ExpressionStatement", "require", "assert"]:
        processing_expression_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    elif now_node.node_type == "Return":
        processing_return_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    elif now_node.node_type == "BinaryOperation":
        processing_binary_operation(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    else:
        processing_other_node(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path)
    # 代表这个函数已经经过操作了，不需要重复操作。
    function_definition_node.attribute["data_flow"] = True


# 遇见控制流的分岔路口的处理方式，参数就是原始函数直接传下来的。
def processing_control_flow_forks(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    # 遍历其中每一个控制流的路径，走下去。
    for control_child_of_now_node in now_node.control_childes:
        # 将当前节点加入到路径列表中，因为代表这个节点已经走过了。
        path.append(now_node)
        # 开始走向下一个控制流节点，在这种控制流的分岔路口，除了路径需要增加，别的都没有需要改变的。
        traverse_function_definition_node(function_definition_node, control_child_of_now_node, pre_variable_node_list, method_params, method_returns, path)
        # 弹出当前的节点。
        path.pop(-1)


# 遇见VariableDeclarationStatement的处理方式，参数就是原始函数直接传下来的。
def processing_variable_declaration_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    variable_declaration_statement_node = now_node
    # 等式左边的字典值,如果是调用的函数有多返回值的时候，就会有多个，所以需要用列表包装。
    declarations_dict_list = []
    # 遍历赋值对象的这个属性，可以获取所有被赋值对象的信息。
    for declarations_dict in variable_declaration_statement_node.attribute['declarations'][0]:
        # 如果是None代表返回值是_，不需要接受，直接略过就行。
        # 所以保存在列表中的内容是字典的列表，每一个元素含有的键分别有node, node_id, node_type, name
        if declarations_dict is not None:
            declarations_dict_list.append({"node": None, "node_id": declarations_dict["id"], "node_type": declarations_dict["nodeType"], "name": declarations_dict["name"]})
    # 等式右边的内容字典
    if "initialValue" in variable_declaration_statement_node.attribute.keys() and variable_declaration_statement_node.attribute['initialValue'][0] is not None:
        initial_value_dict = variable_declaration_statement_node.attribute['initialValue'][0]
        initial_node_id = initial_value_dict['id']
        initial_node_type = initial_value_dict['nodeType']
        initial_node = None
    else:
        initial_node_id = None
        initial_node_type = None
        initial_node = None
    # 先识别当前节点的子结点中谁是等式左端的内容，谁是等式右端的内容。
    for child_of_variable_declaration_statement_node in variable_declaration_statement_node.childes:
        # 当前遍历元素的节点id和节点类型。
        node_id = child_of_variable_declaration_statement_node.node_id
        node_type = child_of_variable_declaration_statement_node.node_type
        # 因为有多个返回值需要识别，所以需要套一层循环，所以需要使用一个flag来识别，内层循环是否找到了对应的节点。
        have_node_flag = False
        # 遍历所有的返回值节点，看看有没有符合条件的
        for node_in_declarations_dict_list in declarations_dict_list:
            # 如果符合条件，就将node字段记录为当前的这个节点，同时设定flag为True，这样子就不会和下面进行匹配了。
            if node_id == node_in_declarations_dict_list['node_id'] and node_type == node_in_declarations_dict_list['node_type']:
                node_in_declarations_dict_list['node'] = child_of_variable_declaration_statement_node
                have_node_flag = True
                break
        # 只要返回值没有匹配上的时候，才有可能是去匹配参数值,也就是等式右端。
        if have_node_flag is False and (node_id == initial_node_id and node_type == initial_node_type):
            initial_node = child_of_variable_declaration_statement_node
    # 如果右半部分确实是存在的
    if initial_node:
        # 获取右半边的返回值是谁，并将右端所有的子节点先处理完毕，因为是在右端，所以如果底层需要连接之前的参数那一定是作为目标，所以是is_src是False，同时不在等式左端，所以is_assignment_left也是False。
        res = get_return(initial_node, pre_variable_node_list, method_params, False, False)
        # 遍历等式左边所有的内容
        for index, node_in_declarations_dict_list in enumerate(declarations_dict_list):
            # 如果对应的等式右边有值，那就将他们相互对应连接起来。
            if index < len(res):
                res[index].append_data_child(node_in_declarations_dict_list['node'])
    # 遍历等式左端的部分，将每一个元素都与之前的同名元素相连接，注意这里是作为出发点，因为是修改覆盖了之前的元素。
    for node_in_declarations_dict_list in declarations_dict_list:
        # 将当前这些返回值都作为起点，连接上之前的部分。
        link_pre_node(pre_variable_node_list, method_params, node_in_declarations_dict_list['node'], node_in_declarations_dict_list['name'], True)
    # 接下来是回溯的内容
    # function_definition_node:不需要修改的
    # now_node:需要改变为控制流子节点
    # pre_variable_node_list:不需要改变
    # method_params:需要改变
    # method_params:不需要改变
    # path:需要改变
    for control_child_of_variable_declaration_statement_node in variable_declaration_statement_node.control_childes:
        # 添加路径走过的节点
        path.append(variable_declaration_statement_node)
        # 添加新的参数
        for node_in_declarations_dict_list in declarations_dict_list:
            method_params.append(node_in_declarations_dict_list['node'])
        # 进行回溯的操作，继续走下一步。
        traverse_function_definition_node(function_definition_node, control_child_of_variable_declaration_statement_node, pre_variable_node_list, method_params, method_returns, path)
        # 回退步骤，将所有的参数回退到原始状态。
        for _ in declarations_dict_list:
            method_params.pop(-1)
        # 将路径也回退回原始状态。
        path.pop(-1)


# 处理ExpressionStatement的时候使用的方法，参数直接沿用原始的数据流处理函数参数。
def processing_expression_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    expression_statement_node = now_node
    # 一般来说,Expression类型的节点都只会有一个子节点，把他的子节点都处理完毕，注意这里都直接设定为False好了，如果有Assignment节点，后面再处理。
    res = get_return(expression_statement_node.childes[0], pre_variable_node_list, method_params, False, False)
    # 进行深度遍历，判断是不是等式。
    stack = LifoQueue(maxsize=0)
    stack.put(now_node)
    # 标记代表当前的语句是不是赋值语句。
    assignment_flag = False
    while not stack.empty():
        pop_node = stack.get()
        if pop_node.node_type == "Assignment":
            assignment_flag = True
            break
        for child in pop_node.childes:
            stack.put(child)
    # 如果是赋值语句，将返回的所有的内容都往之前的部分相连接。
    if assignment_flag:
        # 返回节点是需要特别操作的,也就是说当前节点需要连接上之前被覆盖的那个节点,而且要注意是不是多返回值。
        for node in res:
            if "name" in node.attribute.keys():
                node_name = node.attribute["name"]
                # 注意要逆向，因为要覆盖最近的
                link_pre_node(pre_variable_node_list, method_params, node, node_name, True)
        # 增加新的参数，这里是多余的呜呜呜
        # for node in res:
        #     method_params.append(node)
    # 接下来是回溯的内容
    # function_definition_node:不需要修改的
    # now_node:需要改变为控制流子节点
    # pre_variable_node_list:不需要改变
    # method_params:不需要改变
    # method_params:不需要改变
    # path:需要改变
    for control_child_of_expression_statement_node in expression_statement_node.control_childes:
        # 添加路径走过的节点
        path.append(expression_statement_node)
        for param in res:
            method_params.append(param)
        # 进行回溯的操作，继续走下一步。
        traverse_function_definition_node(function_definition_node, control_child_of_expression_statement_node, pre_variable_node_list, method_params, method_returns, path)
        for _ in res:
            method_params.pop(-1)
        # 将路径也回退回原始状态。
        path.pop(-1)


# 如果是连接return的操作
def processing_return_statement(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    return_node = now_node
    # 对return的所有子节点进行同等操作。
    for child_of_return_node in return_node.childes:
        # 返回值反正不需要和之前的部分主动连接，就不用获取了，另外，肯定是作为目标点，所以is_src是False。并且不是在等式的左端，最后一个is_assignment_left也是False。
        get_return(child_of_return_node, pre_variable_node_list, method_params, False, False)
    # 如果没有子节点，那就根本不需要来连接，因为语句一定是return;
    if return_node.childes:
        # 找出所有在return中返回的组件,这种情况代表的是使用了多返回值。
        if "components" in return_node.attribute["expression"][0].keys():
            # 代表所有可以直接连接出参的组件部分。
            components = []
            # 获取这个子树下所有的内容，用来查询谁连接返回值使用。
            node_list = []
            stack = LifoQueue(maxsize=0)
            stack.put(return_node)
            node_list.append(return_node)
            # 经过深度遍历，获取了return下面每一个子节点
            while not stack.empty():
                pop_node = stack.get()
                for child in pop_node.childes:
                    node_list.append(child)
                    stack.put(child)
            # 通过遍历每一个出参，获取出参的详细信息，这样就能知道刚刚遍历出来的结果，哪些是可以直接连接到出参上的。
            for component_dict in return_node.attribute["expression"][0]["components"]:
                component_node_id = component_dict["id"]
                component_node_type = component_dict["nodeType"]
                for node in node_list:
                    if node.node_id == component_node_id and node.node_type == component_node_type:
                        components.append({"node": node, "node_id": component_node_id, "node_type": component_node_type})
            # 按照两个列表中的顺序，一起连接。
            for return_param, component in zip(method_returns, components):
                component["node"].append_data_child(return_param)
        else:
            expression_node_id = return_node.attribute["expression"][0]["id"]
            expression_node_type = return_node.attribute["expression"][0]["nodeType"]
            expression_node = None
            for node in return_node.childes:
                if node.node_id == expression_node_id and node.node_type == expression_node_type:
                    expression_node = node
            # 这是一种特殊情况，当return test()，但是这个函数如果没有返回值的时候，其实是连不上的。因为当前的本身没有返回值去接收。
            if method_returns:
                expression_node.append_data_child(method_returns[0])
    # 接下来是回溯的内容
    # function_definition_node:不需要修改的
    # now_node:需要改变为控制流子节点
    # pre_variable_node_list:不需要改变
    # method_params:不需要改变
    # method_params:不需要改变
    # path:需要改变
    for control_child_of_return_node in return_node.control_childes:
        # 添加路径走过的节点
        path.append(return_node)
        # 进行回溯的操作，继续走下一步。
        traverse_function_definition_node(function_definition_node, control_child_of_return_node, pre_variable_node_list, method_params, method_returns, path)
        # 将路径也回退回原始状态。
        path.pop(-1)


# 遇见binaryOperation的时候的处理方法
def processing_binary_operation(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    binary_operation_node = now_node
    # 同理,返回值不用操作,而且必定不是作为赋值对象也不在等式左端.
    get_return(binary_operation_node, pre_variable_node_list, method_params, False, False)
    # 接下来是回溯的内容
    # function_definition_node:不需要修改的
    # now_node:需要改变为控制流子节点
    # pre_variable_node_list:不需要改变
    # method_params:不需要改变
    # method_params:不需要改变
    # path:需要改变
    for control_child_of_binary_operation_node in binary_operation_node.control_childes:
        # 添加路径走过的节点
        path.append(binary_operation_node)
        # 进行回溯的操作，继续走下一步。
        traverse_function_definition_node(function_definition_node, control_child_of_binary_operation_node, pre_variable_node_list, method_params, method_returns, path)
        # 将路径也回退回原始状态。
        path.pop(-1)


def processing_other_node(function_definition_node, now_node, pre_variable_node_list, method_params, method_returns, path):
    other_node = now_node
    get_return(other_node, pre_variable_node_list, method_params, False, False)
    # 接下来是回溯的内容
    # function_definition_node:不需要修改的
    # now_node:需要改变为控制流子节点
    # pre_variable_node_list:不需要改变
    # method_params:不需要改变
    # method_params:不需要改变
    # path:需要改变
    for control_child_of_now_node in now_node.control_childes:
        # 添加路径走过的节点
        path.append(now_node)
        # 进行回溯的操作，继续走下一步。
        traverse_function_definition_node(function_definition_node, control_child_of_now_node, pre_variable_node_list, method_params, method_returns, path)
        # 将路径也回退回原始状态。
        path.pop(-1)


# 将当前的节点和之前出现过的变量进行连接。
# pre_variable_node:代表预定义的参数列表。
# method_params:代表当前函数使用的入参，以及在这条控制流出现过的所有参数。
# node:代表本轮的中心是谁。
# node_name:代表当前节点的名字，这个直接写在里面不是很适配，还是从外面按照不同的情况传进去比较好。
# is_src:代表是不是作为起始点，内容是True和False。
def link_pre_node(pre_variable_node_list, method_params, node, node_name, is_src):
    # 也就是说当前的节点作为源节点，直接连上之前的节点，即当前是赋值操作，修改了之前的值，只连接最近的一个。
    flag = False
    # 先从method_param中进行倒序遍历，以获取是来自于谁，如果没有找到，再去找pre_variable_node的问题。
    for method_param_node in method_params[::-1]:
        # 现在的method_params中可能会带上MemberAccess和IndexAccess等这一类没有name属性的节点,所以需要特殊处理.
        if "name" in method_param_node.attribute.keys():
            if method_param_node.attribute['name'] == node_name:
                if is_src:
                    # 注意方向，如果是源，那就当前节点作为父节点，否则反向。
                    node.append_data_child(method_param_node)
                else:
                    method_param_node.append_data_child(node)
                # 如果找到了就修改标志符，并退出循环。
                flag = True
                break
    # 如果在之前的参数列表中还没有出现过，那说明使用的就是全局变量。
    if not flag:
        # 遍历所有的预定义参数节点
        for pre_variable_node in pre_variable_node_list:
            # 取出其中的参数名字
            pre_variable_node_name = pre_variable_node.attribute['name']
            # 判断这个名字是不是列表类型，如果是就取0
            if isinstance(pre_variable_node_name, list):
                pre_variable_node_name = pre_variable_node_name[0]
            # 这里也是要判断的，因为好像有的情况会带一个列表。
            if isinstance(node_name, list):
                node_name = node_name[0]
            # 如果与定义参数的名字等于当前节点的名字，那就连接。
            if pre_variable_node_name == node_name:
                # 注意方向，如果是源，那就当前节点作为父节点，否则反向。
                if is_src:
                    node.append_data_child(pre_variable_node)
                else:
                    pre_variable_node.append_data_child(node)
                # 找到了就退出循环，不用再做无用功。
                break


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


# 获取以传入的节点为根的树的返回节点应该是谁,注意返回的内容已经修改为了列表。
# is_src:代表是不是以当前节点为源节点，因为要控制连接之前节点的方向。
# is_assignment_left:判断是不是等式左边的部分。
def get_return(initial_node, pre_variable_node_list, method_params, is_src, is_assignment_left):
    # 如果是这几类节点,说明已经到了底端了,不需要继续深入了.
    if initial_node.node_type in ["Identifier", "Literal", "ElementaryTypeNameExpression", "NewExpression"]:
        # 既要含有name属性，还得保证不在等号左端,注意如果是在等号左端是需要特殊处理的.
        if "name" in initial_node.attribute.keys() and is_assignment_left is False:
            # 直接连上之前使用过的属性,方向自己设定.
            link_pre_node(pre_variable_node_list, method_params, initial_node, initial_node.attribute['name'], is_src)
        return [initial_node]
    # 需要递归处理的部分.
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
        # 分别找出三种节点是谁。
        for child_of_conditional_node in conditional_node.childes:
            # 如果其中某一个是还需要进一步细化的，那就继续往下找。
            if child_of_conditional_node.node_type in need_recursion_types:
                if child_of_conditional_node.node_id == condition_node_node_id and child_of_conditional_node.node_type == condition_node_node_type:
                    condition_node = get_return(child_of_conditional_node, pre_variable_node_list, method_params, False, is_assignment_left)[0]
                elif child_of_conditional_node.node_id == false_expression_node_id and child_of_conditional_node.node_type == false_expression_node_type:
                    false_expression_node = get_return(child_of_conditional_node, pre_variable_node_list, method_params, False, is_assignment_left)[0]
                elif child_of_conditional_node.node_id == true_expression_node_id and child_of_conditional_node.node_type == true_expression_node_type:
                    true_expression_node = get_return(child_of_conditional_node, pre_variable_node_list, method_params, False, is_assignment_left)[0]
            else:
                if child_of_conditional_node.node_id == condition_node_node_id and child_of_conditional_node.node_type == condition_node_node_type:
                    condition_node = child_of_conditional_node
                elif child_of_conditional_node.node_id == false_expression_node_id and child_of_conditional_node.node_type == false_expression_node_type:
                    false_expression_node = child_of_conditional_node
                elif child_of_conditional_node.node_id == true_expression_node_id and child_of_conditional_node.node_type == true_expression_node_type:
                    true_expression_node = child_of_conditional_node
        # 将两种情况节点作为父节点，连接到条件节点上。
        false_expression_node.append_data_child(condition_node)
        true_expression_node.append_data_child(condition_node)
        return [condition_node]
    # 如果是成员变量,只有一个子，直接获取子并返回。
    elif initial_node.node_type == "MemberAccess":
        member_access_node = initial_node
        res = get_return(member_access_node.childes[0], pre_variable_node_list, method_params, False, is_assignment_left)[0]
        # 不要将他们连起来，没有数据流的关系
        res.append_data_child(member_access_node)
        if is_assignment_left:
            member_access_node.append_data_child(res)
            return [member_access_node, res]
        return [member_access_node]
        # return [res]
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
        # 分别找出两种节点
        for child in index_access_node.childes:
            # 如果是需要继续递归的，那就先递归，然后通过递归的返回的元素作为连接的节点。
            if child.node_id == base_expression_node_node_id and child.node_type == base_expression_node_node_type:
                base_expression_node = get_return(child, pre_variable_node_list, method_params, False, is_assignment_left)[0]
            elif child.node_id == index_expression_node_node_id and child.node_type == index_expression_node_node_type:
                # 这里需要设置固定不是等号左端，不然下标就不会引用之前的变量了。
                index_expression_node = get_return(child, pre_variable_node_list, method_params, False, False)[0]
        # 以下需要设置的几条边有:数组自己指向IndexAccess，下标指向IndexAccess，两者组合给IndexAccess使用，然后再由IndexAccess连到数组上，代表发生了改变，并将IndexAccess返回。
        base_expression_node.append_data_child(index_access_node)
        index_expression_node.append_data_child(index_access_node)
        if is_assignment_left:
            index_access_node.append_data_child(base_expression_node)
            return [index_access_node, base_expression_node]
        else:
            return [index_access_node]
    # 如果是Tuple，其实可以忽略，但是依然需要向下移动。
    elif initial_node.node_type == "TupleExpression":
        tuple_expression_node = initial_node
        # 传入tuple的子节点，然后直接返回，这样就不会连接到tuple上。
        if tuple_expression_node.childes:
            res = []
            for child in tuple_expression_node.childes:
                for tmp in get_return(child, pre_variable_node_list, method_params, False, is_assignment_left):
                    res.append(tmp)
            return res
        else:
            return []
    # 如果是这种情况，需要获取两个不需要递归计算的返回值，将两个返回值连接到BinaryOperation节点上，同时返回BinaryOperation节点。
    elif initial_node.node_type == "BinaryOperation":
        binary_operation_node = initial_node
        res1 = None
        res2 = None
        # 搜索每一个子节点中可以直接连接Binary的节点
        for index, child_of_binary_operation_node in enumerate(binary_operation_node.childes):
            # 如果是需要递归的部分，那就先递归。
            if index == 0:
                res1 = get_return(child_of_binary_operation_node, pre_variable_node_list, method_params, False, is_assignment_left)
            if index == 1:
                res2 = get_return(child_of_binary_operation_node, pre_variable_node_list, method_params, False, is_assignment_left)
        # 将这两个返回值都连接到BinaryOperation节点上。
        for child_of_res1 in res1:
            child_of_res1.append_data_child(binary_operation_node)
        for child_in_res2 in res2:
            child_in_res2.append_data_child(binary_operation_node)
        # 同时返回自己。
        return [binary_operation_node]
    # 如果是UnaryOperation，需要获取一个返回节点，而且返回节点需要连接当前的unaryOperation节点，并返回子节点。
    elif initial_node.node_type == "UnaryOperation":
        unary_operation_node = initial_node
        res = get_return(unary_operation_node.childes[0], pre_variable_node_list, method_params, False, is_assignment_left)[0]
        if "name" in res.attribute.keys():
            link_pre_node(pre_variable_node_list, method_params, res, res.attribute['name'], True)
        return [res]
    # 如果是Assignment节点，需要获取两个返回节点的时候，答案节点需要连接到结果节点上，然后返回结果节点。
    elif initial_node.node_type == "Assignment":
        assignment = initial_node
        left_hand_side = None
        right_hand_side = None
        # 搜索每一个子节点中可以直接连接Assignment的节点。
        for index, child_of_assignment in enumerate(assignment.childes):
            if index == 0:
                left_hand_side = get_return(child_of_assignment, pre_variable_node_list, method_params, True, True)
            if index == 1:
                right_hand_side = get_return(child_of_assignment, pre_variable_node_list, method_params, False, False)
        # 如果左右个数不一致,这说明是使用了加减乘除，如果是一致且多个，那就是说多返回值。
        if len(left_hand_side) != len(right_hand_side):
            for right in right_hand_side:
                right.append_data_child(left_hand_side[0])
        else:
            # 将答案节点连接到结果节点上。
            for index, _ in enumerate(left_hand_side):
                right_hand_side[index].append_data_child(left_hand_side[index])
        return left_hand_side
    # 可以将所有的参数连接到对应的入参上，然后将所有的出参返回回来，作为一个列表。
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
        # 遍历其中所有的子节点，分配角色。
        for child_of_function_call_node in function_call_node.childes:
            child_node_id = child_of_function_call_node.node_id
            child_node_type = child_of_function_call_node.node_type
            if not (child_node_id == expression_node_node_id and child_node_type == expression_node_node_type):
                for argument in arguments:
                    if child_node_id == argument["node_id"] and child_node_type == argument["node_type"]:
                        argument["node"] = get_return(child_of_function_call_node, pre_variable_node_list, method_params, False, is_assignment_left)[0]
            # 那剩下的就是函数调用节点,里面的部分也是需要使用get_Return来操作的
            else:
                get_return(child_of_function_call_node, pre_variable_node_list, method_params, False, is_assignment_left)
        # 找出FunctionCall的控制流子节点，判断其中是否含有FunctionDefinition节点，如果有，那就说明是内部函数调用，那么当前的expression_node需要连接到所有的入参上。
        for control_child in function_call_node.control_childes:
            if control_child.node_type == "FunctionDefinition":
                # 将当前这一行调用的参数连接到对应函数的入参上。
                method_params, method_returns = get_method_message_at_function_definition_node(control_child)
                for param in zip(arguments, method_params):
                    param[0]["node"].append_data_child(param[1])
                # 返回出参，供下一次使用。
                return method_returns
        # 能到达这里说明不是内部函数,那就直接将所有的入参全部连接到FunctionCallNode上.记得还要引用来自之前的部分.
        for argument_node in arguments:
            argument_node["node"].append_data_child(function_call_node)
            get_return(argument_node["node"], pre_variable_node_list, method_params, False, False)
        # 如果不是内部函数，那就直接返回函数调用节点
        return [function_call_node]
