# coding=UTF-8


# 设置函数的method_name等详细信息到attribute上。
def append_method_message_by_dict(project_node_dict, data_sol_source_project_dir_path):
    # 存在函数的情况下才调用这段代码
    if "FunctionDefinition" in project_node_dict.keys():
        # 循环所有的FunctionDefinition节点，找出其中的method_name作为新的属性。
        for node in project_node_dict['FunctionDefinition']:
            # 为了取出方法的名字，先获取start和end，然后去切分字符串。
            end = node.attribute['src_code'][0].index(")") + 1
            start_left_symbol = node.attribute['src_code'][0].index("(") + 1
            # 如果找的到空格键,那说明是正常的，找不到的话说明提取不出来，直接start用0就行。
            if node.attribute['src_code'][0].find(" ") != -1:
                blank_index = node.attribute['src_code'][0].index(" ") + 1
            else:
                blank_index = start_left_symbol
            # 如果是先出现左括号，再出现空格，那就有问题。
            if start_left_symbol <= blank_index:
                start = 0
            else:
                start = node.attribute['src_code'][0].index(" ") + 1
            # 切分字符串，获取函数的完全信息
            # function call(uint a) public pure returns(uint){
            # 假如上面这个例子，取出来的是call(uint a)
            method_full_content = node.attribute['src_code'][0][start: end]
            # 如果长度是0，或者第一个元素是(，都是说明当前的函数是构造函数
            if len(method_full_content) == 0 or method_full_content[0] == "(":
                ancestor = node
                # 只要还没有到达合约的节点，就一直网上寻找，直到找到合约的名字，作为构造的方法。
                while not ancestor.node_type == "ContractDefinition":
                    ancestor = ancestor.parent
                    # 找到了合约定义的地方，使用合约的名字作为函数名
                    if ancestor.node_type == "ContractDefinition":
                        # 这个是函数的名字,保存下来的是ContractName这样子,没有括号也没有参数
                        method_name = ancestor.attribute['name'][0]
                        # 被切分以后的参数名字
                        after_split_params = method_full_content.replace("(", "").replace(")", "").split(",")
                        # 存放最终的参数的数组，使用数组，里面只保存对应的参数的类型。
                        params = []
                        # 这里取到的部分还是uint a这种，还需要再次切分
                        for param in after_split_params:
                            # 如果长度是0，直接跳过。
                            if len(param) == 0:
                                continue
                            # 需要考虑到后面的参数会有空格开头的情况，比如function main(uint a, uint b)
                            if param.split(" ")[0] != "":
                                params.append(param.split(" ")[0])
                            else:
                                params.append(param.split(" ")[1])
                        # 将这里的函数名字和参数都添加到FunctionDefinition节点的attribute上。
                        node.append_attribute("method_name", method_name)
                        node.append_attribute("params", params)
            # 说明不是构造函数，是普通函数
            else:
                # 取出main(uint a, uint b)中的函数名字。
                method_name = method_full_content[0: method_full_content.index("(")]
                # 存放最终的参数的数组，使用数组，里面只保存对应的参数的类型。
                params = []
                # 被切分以后的参数名字，这里面保存的是['uint a', ' uint b',...]
                after_split_params = method_full_content.replace(method_name, "").replace("(", "").replace(")", "").split(",")
                # 这里取到的部分还是uint a这种，还需要再次切分
                for param in after_split_params:
                    # 如果长度是0，直接跳过。
                    if len(param) == 0:
                        continue
                    # 需要考虑到后面的参数会有空格开头的情况，比如function main(uint a, uint b)
                    if param.split(" ")[0] != "":
                        params.append(param.split(" ")[0])
                    else:
                        params.append(param.split(" ")[1])
                # 将这里的函数名字和参数都添加到FunctionDefinition节点的attribute上。
                node.append_attribute("method_name", method_name)
                node.append_attribute("params", params)
    # 如果存在修饰符才启动这段代码
    if "ModifierDefinition" in project_node_dict.keys():
        # 循环所有的ModifierDefinition节点，找出其中的method_name作为新的属性。
        for node in project_node_dict['ModifierDefinition']:
            # 为了取出方法的名字，先获取start和end，然后去切分字符串。
            start = node.attribute['src_code'][0].index(" ") + 1
            # 修饰符有的时候可能不是以函数的形式出现的
            # modifier lockTheSwap {
            #   _;
            # }
            if node.attribute['src_code'][0].__contains__(")"):
                end = node.attribute['src_code'][0].index(")") + 1
            else:
                # 直接取出start,end之间的内容，这样子只有函数名，没有参数
                end = node.attribute['src_code'][0].find(" ", start)
                node.append_attribute("method_name", node.attribute['src_code'][0][start: end])
                node.append_attribute("params", [])
                continue
            # 切分字符串，获取函数的完全信息
            # modifier onlyOwner(uint a) {
            # 假如上面这个例子，取出来的是onlyOwner(uint a)
            method_full_content = node.attribute['src_code'][0][start: end]
            # 取出onlyOwner(uint a)中的函数名字，onlyOwner
            method_name = method_full_content[0: method_full_content.index("(")]
            # 存放最终的参数的数组，使用数组，里面只保存对应的参数的类型。
            params = []
            # 被切分以后的参数名字，这里面保存的是['uint a', ' uint b',...]
            after_split_params = method_full_content.replace(method_name, "").replace("(", "").replace(")", "").split(",")
            # 这里取到的部分还是uint a这种，还需要再次切分
            for param in after_split_params:
                # 如果长度是0，直接跳过。
                if len(param) == 0:
                    continue
                # 需要考虑到后面的参数会有空格开头的情况，比如onlyOwner(uint a, uint b)
                if param.split(" ")[0] != "":
                    params.append(param.split(" ")[0])
                else:
                    params.append(param.split(" ")[1])
            # 将这里的函数名字和参数都添加到ModifierDefinition节点的attribute上。
            node.append_attribute("method_name", method_name)
            node.append_attribute("params", params)
    print(f"{data_sol_source_project_dir_path}函数信息更新成功")
