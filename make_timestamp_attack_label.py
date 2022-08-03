from queue import LifoQueue
import datetime
import config
import utils


# 判断文件中是否含有时间戳的漏洞。
def make_timestamp_attack_label(project_node_dict, file_name):
    # 进入函数的时间
    enter_time = datetime.datetime.now()
    # 如果是generate_all，并不需要继续操作，因为这时候在create_corpus_txt的时候已经生成过标签了。
    if config.create_corpus_mode == "generate_all":
        return
    # 默认没有时间戳攻击，只有当发现了时间戳攻击的时候，才会修改标签
    timestamp_flag = False
    # 记录回溯的操作结果的
    has_timestamp_flag = []
    # 遍历所有的合约节点，从下面的参数block去出发。
    for contract_node in project_node_dict['ContractDefinition']:
        # 如果在某一次循环中已经发现当前文件中是带有漏洞的，那就直接可以直接退出循环得出答案了。
        if timestamp_flag:
            break
        # 遍历ContractDefinition节点下面的子节点，这些子节点就是预定义参数的节点。
        for block_node in contract_node.childes:
            if timestamp_flag:
                break
            # 找到了block节点，开始进行时间戳漏洞检测，对block的数据流进行回溯。
            if block_node.node_type == "VariableDeclaration" and block_node.attribute["name"][0] == "block":
                # 遍历每一个block属性节点的数据流子节点,如果发现是用在了block.timestamp上，那就从该节点开始回溯。
                for data_child in block_node.data_childes:
                    # 需要该节点的子节点数量不为0，而且是MemberAccess类型，而且内容是timestamp，才能称之为时间戳节点。
                    if len(data_child.data_childes) != 0 and data_child.data_childes[0].node_type == "MemberAccess" and data_child.data_childes[0].attribute["src_code"][0] == "block.timestamp":
                        # 取出时间戳节点，该节点作为回溯的出发节点。
                        block_timestamp_node = data_child.data_childes[0]
                        traverse_timestamp_flag(block_timestamp_node, [], has_timestamp_flag, block_timestamp_node, enter_time)
                        if len(has_timestamp_flag):
                            timestamp_flag = True
                            break
    print(f"{file_name}时间戳标签已经检测完毕。")
    # 最终返回这个控制的变量即可。
    if timestamp_flag:
        return has_timestamp_flag[0]
    else:
        return 0


# 进行基于block属性的回溯遍历
# block_timestamp_node:block_timestamp属性节点。
# path:用来标记已经走过的路线，避免重复走。
# has_timestamp_flag：用来标记结果的
# now_node:当前的位置，一开始进来的时候和block_timestamp_node是同一个节点。
def traverse_timestamp_flag(block_timestamp_node, path, has_timestamp_flag, now_node, enter_time):
    # 此刻的时间
    now_time = datetime.datetime.now()
    # 说明打标签的时间太长了,同时要注意，将源代码的sol
    if (now_time - enter_time).seconds > config.make_timestamp_attack_label_max_time:
        raise utils.CustomError("时间戳漏洞标签耗时过久，已被移入error文件夹")
    # 如果已经找到漏洞了，不再进行遍历。
    if len(has_timestamp_flag):
        return
    count = 0
    for node in path:
        if now_node == node:
            count += 1
    # 出现了两次重复就断开。
    if count >= 2:
        return
    should_operation_flag = True
    # 如果是require或者assert的部分，不需要进行判断，直接进行下一步的回溯即可
    if node_in_assign_subdomain(now_node, "require") or node_in_assign_subdomain(now_node, "assert"):
        # 修改标记，代表不用进行操作，可以直接返回。
        should_operation_flag = False
    # 遍历所有的数据流子节点，进行回溯操作。
    for data_child in now_node.data_childes:
        # 如果该节点已经走过了，进行深入判断，看看是不是控制流让走的，如果不是控制流让走的，那就直接略过，因为正式运行的时候，是无法走回去的。
        if data_child in path:
            # 如果并不是控制流可以走的路线，直接略过
            if data_child_is_now_node_control_child(data_child, now_node) is False:
                continue
        path.append(now_node)
        # 需要操作的时候，才进行节点操作。
        if should_operation_flag:
            # 需要操作的时候，进行时间戳漏洞判断。
            res = timestamp_attack(now_node)
            if res == 1:
                has_timestamp_flag.append(1)
            if res == 2:
                has_timestamp_flag.append(2)
        traverse_timestamp_flag(block_timestamp_node, path, has_timestamp_flag, data_child, enter_time)
        path.pop(-1)


# 判断节点是否在指定类型的节点的子域中。返回True代表是，否则代表不是。
def node_in_assign_subdomain(node, assign_node_type):
    while True:
        if node.node_type == assign_node_type:
            return True
        node = node.parent
        if node is None:
            return False


# 判断data_child是不是now_node的最近的控制流节点的控制流子节点。
def data_child_is_now_node_control_child(data_child, now_node):
    control_node_of_data_child = data_child
    while True:
        # 如果存在控制流，那就说明找到了
        if control_node_of_data_child.node_type in ["ForStatement", "WhileStatement", "DoWhileStatement"]:
            break
        control_node_of_data_child = control_node_of_data_child.parent
        # 如果是None，那只能说明是预定义的参数，那肯定可以走到的，直接返回True。
        if control_node_of_data_child is None:
            return True
    control_node_of_now_node = now_node
    while True:
        # 如果存在控制流，那就说明找到了
        if control_node_of_now_node.node_type in ["ForStatement", "WhileStatement", "DoWhileStatement"]:
            break
        control_node_of_now_node = control_node_of_now_node.parent
        # 如果是None，那只能说明是预定义的参数，那肯定是走不到的，直接返回False。
        if control_node_of_now_node is None:
            return False
    # 如果两个人在同一个循环中，那就可代表有希望走到。
    if control_node_of_data_child == control_node_of_now_node:
        return True
    else:
        return False


# 判断节点是不是判定条件节点，如果是，返回对应的block或者语句。
def node_is_condition_node(node):
    while True:
        # 如果是这几种类型，直接返回节点。
        if node.node_type in ["IfStatement", "ForStatement", "DoWhileStatement", "WhileStatement"]:
            return node
        node = node.parent
        if node is None:
            return None


# 进行时间戳漏洞检测,确定有漏洞返回1，如果疑似漏洞返回2，否则返回0.
def timestamp_attack(now_node):
    # 先获取判定条件所处在的四种控制流节点。
    res = node_is_condition_node(now_node)
    if res is not None:
        # 接下来只要简单的判定其中是否带有return或者转账的操作
        stack = LifoQueue(maxsize=0)
        stack.put(res)
        while not stack.empty():
            pop_node = stack.get()
            # 如果含有转账函数或者return的部分，那就直接返回1
            if pop_node.node_type == "FunctionCall" and (pop_node.attribute["src"][0].__contains__("call.value") or pop_node.attribute["src"][0].__contains__("transfer")):
                return 1
            if pop_node.node_type == "Return":
                return 1
            for child in pop_node.childes:
                stack.put(child)
    # 如果不是上面四种控制流节点，那就要判断是不是return底下的部分，如果是，那也会构成。
    if node_in_assign_subdomain(now_node, "Return"):
        return 1
    # 经过上面的操作，都没有发现问题。
    return 0
