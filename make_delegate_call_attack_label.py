from queue import LifoQueue
import utils
import config


def make_delegate_call_attack_label(project_node_dict, file_name):
    # 如果是generate_all，并不需要继续操作，因为这时候在create_corpus_txt的时候已经生成过标签了。
    if config.create_corpus_mode == "generate_all":
        return
    delegate_flag = False
    has_delegate_call_flag = []
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
                    if "memberName" in child.attribute.keys() and child.attribute["memberName"][0] == "delegatecall":
                        # 因为child代表的是MemberAccess这个节点，所以需要取出他的调用者，也就是他的抽象语法树的子节点
                        identifier_call_node = child.childes[0]
                        # 找出所有的上级数据流节点
                        origin_list = []
                        stack = LifoQueue(maxsize=0)
                        stack.put(identifier_call_node)
                        while not stack.empty():
                            pop_node = stack.get()
                            # 如果遍历过，那就跳过，否则判断该节点的父节点是不是来自于入参。
                            if pop_node in origin_list:
                                continue
                            origin_list.append(pop_node)
                            # 获取该节点的数据流父节点
                            res = pop_node.data_parents
                            # 将这些父节点压入到栈中，以进行深度遍历。
                            for origin_node in res:
                                stack.put(origin_node)
                            # 如果当前循环的元素的父节点是ParameterList，代表这个参数是来源于入参的，也就是容易被攻击。
                            if pop_node.parent.node_type == "ParameterList":
                                delegate_flag = True
                                has_delegate_call_flag.append(1)
    utils.success(f"{file_name}危险调用漏洞已经检测完毕。")
    # 最终返回这个控制的变量即可。
    if delegate_flag:
        return has_delegate_call_flag[0]
    else:
        return 0
