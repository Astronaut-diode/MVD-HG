# coding=UTF-8
from queue import Queue
from bean.Node import Node
import os
import json


def read_compile(data_sol_source_project_dir_path, data_ast_json_project_dir_path):
    project_node_list = []
    tmp_file_name = f'{data_ast_json_project_dir_path}/w.json'
    # 遍历工程项目中的每一个文件
    for ast_json_file_name in os.listdir(data_ast_json_project_dir_path):
        # 抽象语法树文件的完全路径,如""/home/xjj/AST-GNN/data/AST_json/project_name/file_name.json"
        full_ast_json_path = f'{data_ast_json_project_dir_path}/{ast_json_file_name}'
        # 为这个语法树文件删除前几行，因为生成的时候前面带上了一些不必要的信息
        with open(full_ast_json_path, 'r') as read_file, open(tmp_file_name, 'w+') as write_file:
            # 判断是否需要开始抄写的触发器
            flag = False
            for index, line in enumerate(read_file.readlines()):
                # 如果已经需要开始记录了，开始抄写，把内容抄到w.json文件中
                if flag:
                    write_file.write(line)
                    continue
                # 如果发现已经到了这一行，那么说明从这里开始已经需要记录了。
                # 使用了新的判断条件，原先的通用性不是很好
                if line.replace("\n", "").__contains__("======="):
                    flag = True
        # 删除原始的json文件，同时将刚刚生成的w.json文件转化为正确的名字。
        os.remove(full_ast_json_path)
        os.rename(tmp_file_name, full_ast_json_path)
        # 正式的开始读取json文件中的内容
        with open(full_ast_json_path, 'r') as ast_json:
            # 使用json的方式加载文件内容
            # 现在如果有问题，在一开始生成json的时候就已经被发现了，会直接被删除掉，而不是等到现在，所以不再需要进行try/catch。
            content = json.load(ast_json)
            # 使用分而治之的方法，把里面的id属性全部加上len(project_node_list)
            update_content(content, len(project_node_list))
            # 将文件中的内容转化为图结构的数据，传入的内容有抽象语法树的内容，当前项目的所有节点列表，还有读入当前文件之前已经有多少个节点了，这个待会进去会变得，所以先记录下来。
            create_graph(content, project_node_list, f'{data_sol_source_project_dir_path}/{ast_json_file_name.replace(".json", ".sol")}')
    # 此时整个工程文件夹中的节点都已经构建完成，将这些节点按照节点类型分类，同时放到字典中，保存的格式{"nodeType1": [...], "nodeType2": [...]}
    project_node_dict = {}
    # 循环工程文件夹内所有的节点，为了将这些节点分类保存起来。
    for node in project_node_list:
        node_type = node.node_type
        # 如果当前元素的节点类型不存在，先创建对应的key，然后再往里面插值
        if node_type not in project_node_dict.keys():
            project_node_dict[node_type] = []
        # 为对应的属性添加对应的节点。
        project_node_dict[node_type].append(node)
    return project_node_list, project_node_dict


# 使用递归的方法，修改content中所有的id属性。
def update_content(content, before_file_project_node_list_len):
    for key in content.keys():
        # 这代表里面可能含有id属性。
        if isinstance(content[key], dict):
            # 使用递归的方法，去递归的操作属性。
            update_content(content[key], before_file_project_node_list_len)
    # 设定里面所有的id属性增加一个长度，而这个长度就是前一个文件读完以后已经有了多少个节点。
    if 'id' in content.keys():
        content['id'] = content['id'] + before_file_project_node_list_len
    # 这个属性也是一样的，需要增加之前文件的节点数量。
    if 'referencedDeclaration' in content.keys():
        content['referencedDeclaration'] = content['referencedDeclaration'] + before_file_project_node_list_len


# 传入一个队列中的内容，然后生成节点
# node_id:节点的id
# node_type:是节点的类型
# parent:当前这个节点的父节点是谁
def create_new_node(node_id, node_type, parent):
    node = Node(node_id, node_type, parent)
    return node


# 根据传入的json内容生成一个简单的AST的树结构数据。
# content:json文件内容
# node_list:在当前工程文件夹中，已经记录的所有节点。
# source_file_name:传入当前源文件的名字，这样子可以再次去读取源文件中的内容，然后根据src的位置去获取当前节点代表的是哪一句语句。
def create_graph(content, node_list, source_file_name):
    # 保存当前源文件源代码的数组，相当于将源代码直接拆分为了['p', 'r', 'a', 'g', ...]这样子，后面直接从中间取出来就知道了节点代表的是哪条语句。
    src = []
    # 将内容进行循环遍历最终记录到上面的src的数组中。
    with open(source_file_name, 'r') as read_file:
        # 读取其中的字符，这样子可以实现后面的源代码对齐。
        for char in read_file.read():
            # 通过utf-8的编码格式进行编码，这样子如果遇见了中文这些汉字可以转化为三个字节，更加的适配。
            # 而且src中的部分也是因为有中文等才会出现不对齐的情况。
            byte_list = bytes(char, encoding="utf-8")
            for byte in byte_list:
                src.append(byte)
    # 创建队列，待会用来保存广度遍历里的东西
    queue = Queue(maxsize=0)
    # 根据内容创建节点，注意这里的id，需要时本身的id加上已经被记录的个数，否则到了下一份文件中，又从0开始就不好了。
    parent_node = create_new_node(content['id'], content['nodeType'], None)
    # 将第一个节点的除了id和nodeType的所有属性，一起添加到节点上。
    for key in content.keys():
        # 如果不是id或者nodeType的属性，直接记录到attribute中，使用字典的形式。
        if not key == 'id' and not key == 'nodeType':
            parent_node.append_attribute(key, content[key])
            queue.put(content[key])
        # 这里代表了源代码的位置，可以直接使用下标从刚刚的源代码数组中切片获取。
        if key == "src":
            # 先获取其中的开始位置和结束的位置
            index_list = content["src"].split(":")
            # 根据开始和结束的位置我们可以截取出其中的字节部分
            src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
            # 根据字节的部分，我们再将其重新转化为原始的内容
            src_content = str(bytes(src_content), encoding="utf-8")
            # 将原始的内容添加到src_code当中。
            parent_node.append_attribute("src_code", "".join(src_content))
    # 先记录当前节点，作为广度遍历的根。
    node_list.append(parent_node)
    # 对之前加入的东西进行遍历。
    while not queue.empty():
        q = queue.get()
        # 如果是字典，说明极有可能是子节点。
        if isinstance(q, dict):
            # 如果含有这两个属性，表明已经是子节点了。
            if 'id' in q.keys() and 'nodeType' in q.keys():
                # 先新增节点，并作如下三个操作。而且一定要记住，因为每个文件都有可能生成节点，所以节点的id不能直接使用，需要修改。
                node = create_new_node(q['id'], q['nodeType'], parent_node)
                # 往队列里插入这个节点，这样子下次找到新的内容就可以更换父节点，就知道谁是谁的父亲了。
                queue.put(node)
                # 当前这个节点是原先的父节点的子节点。
                parent_node.append_child(node)
                # 将其他的属性循环插入到队列中，同时还要切片获取其中的源代码。
                for key in q.keys():
                    if not key == 'id' and not key == 'nodeType':
                        queue.put(q[key])
                        node.append_attribute(key, q[key])
                    if key == "src":
                        # 先获取原始代码转化为byte以后的起始和终止的位置
                        index_list = q["src"].split(":")
                        # 根据开始和结束的位置，截取出byte的串
                        src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
                        # 根据byte的串，我们可以重新转化为原文
                        src_content = str(bytes(src_content), encoding="utf-8")
                        # 将原文添加到对应的属性中。
                        node.append_attribute("src_code", "".join(src_content))
                # 先记录其属性，再记录这个节点
                node_list.append(node)
        # 如果不是字典，是list，可能包含了一串的子节点
        elif isinstance(q, list):
            # 循环遍历里面所有的子对象
            for obj in q:
                # 如果子对象是字典类型
                if isinstance(obj, dict):
                    # 如果含有这两个属性，表明已经是子节点了。
                    if 'id' in obj.keys() and 'nodeType' in obj.keys():
                        # 先新增节点，并作如下三个操作。
                        node = create_new_node(obj['id'], obj['nodeType'], parent_node)
                        # 往队列里插入这个节点，这样子下次找到新的内容就可以更换父节点，就知道谁是谁的父亲了。
                        queue.put(node)
                        # 当前这个节点是原先的父节点的子节点。
                        parent_node.append_child(node)
                        # 将其他的属性循环插入到队列中，同时还要切片获取源代码。
                        for key in obj.keys():
                            if not key == 'id' and not key == 'nodeType':
                                queue.put(obj[key])
                                node.append_attribute(key, obj[key])
                            if key == "src":
                                # 先获取在bytes中的开始的位置和结束的位置
                                index_list = obj["src"].split(":")
                                # 根据开始和结束的位置，我们可以获取对应的byte串
                                src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
                                # 将byte串重新转化为字符串
                                src_content = str(bytes(src_content), encoding="utf-8")
                                # 将字符串直接添加到我们设定好的属性中去。
                                node.append_attribute("src_code", "".join(src_content))
                        # 先记录其属性，再记录这个节点。
                        node_list.append(node)
        # 如果是节点类型，说明需要更换父节点了。
        elif isinstance(q, Node):
            parent_node = q
    print(source_file_name, "create_graph完成")
