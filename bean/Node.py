# coding=UTF-8
class Node:
    # 节点id
    node_id = 0
    # 节点的类型
    node_type = "暂无定义"
    # 父亲节点
    parent = None
    # 儿子节点
    childes = []
    # 用来记录一些属性，如果重要的话后面可以摘出来重新创建类实现。
    attribute = {}
    # 数据流的子节点
    data_childes = []
    # 数据流的父节点
    data_parents = []
    # 控制流的子节点
    control_childes = []
    # 控制流的父节点
    control_parents = []
    # 所属文件的名字
    owner_file = ""
    # 所属合约的名字
    owner_contract = ""
    # 所属函数的名字
    owner_function = ""
    # 所属行
    owner_line = -1

    def __init__(self, node_id, node_type, parent):
        self.node_id = node_id
        self.node_type = node_type
        self.parent = parent
        self.childes = []
        self.attribute = {}
        self.data_childes = []
        self.data_parents = []
        self.control_childes = []
        self.control_parents = []

    def append_child(self, node):
        self.childes.append(node)

    def append_data_child(self, node):
        if node not in self.data_childes:
            self.data_childes.append(node)
            # 反向增加数据流父节点
            node.data_parents.append(self)

    def append_control_child(self, node):
        if node not in self.control_childes:
            self.control_childes.append(node)
            # 反向增加控制流父节点
            node.control_parents.append(self)

    def append_attribute(self, key, value):
        if self.attribute.__contains__(key):
            self.attribute[key].append(value)
        else:
            self.attribute[key] = [value]

    def __str__(self):
        # 这里只显示四位的原因是如果使用matplotlib画图，上面回显的字符串如果太长不是很方便显示。
        return self.node_type[0:4]

    def set_owner_file(self, owner_file):
        self.owner_file = owner_file

    def set_owner_contract(self, owner_contract):
        self.owner_contract = owner_contract

    def set_owner_function(self, owner_function):
        self.owner_function = owner_function

    def set_owner_line(self, owner_line):
        self.owner_line = owner_line
