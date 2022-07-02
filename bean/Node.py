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
    # 控制流的子节点
    control_childes = []

    def __init__(self, node_id, node_type, parent):
        self.node_id = node_id
        self.node_type = node_type
        self.parent = parent
        self.childes = []
        self.attribute = {}
        self.data_childes = []
        self.control_childes = []

    def append_child(self, node):
        self.childes.append(node)

    def append_data_child(self, node):
        self.data_childes.append(node)

    def append_control_child(self, node):
        self.control_childes.append(node)

    def append_attribute(self, key, value):
        if self.attribute.__contains__(key):
            self.attribute[key].append(value)
        else:
            self.attribute[key] = [value]

    def __str__(self):
        # 这里只显示四位的原因是如果使用matplotlib画图，上面回显的字符串如果太长不是很方便显示。
        return self.node_type[0:4]
