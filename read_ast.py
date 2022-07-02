import os
import json
from queue import Queue
import config
from gensim.models.word2vec import Word2Vec
from bean.Node import Node
from print_tree import print_tree
from built_corpus import built_corpus_bfs, built_corpus_dfs

# 在linux环境下的当前工程路径
parent_path = os.getcwd()
# 在data目录下，原始的solidity保存的目录:/home/xjj/AST-GNN/data/sol_source/
data_sol_source_dir_path = parent_path + "/data/sol_source/"
# 在data目录下，生成的ast的json文件的保存目录:/home/xjj/AST-GNN/data/AST_json/
data_ast_json_dir_path = parent_path + "/data/AST_json/"
# 字典的结构是{节点类型:[这个类型的所有节点]}
total_node_list = {}


# 读取刚刚保存下的抽象语法树的json文件
def read_ast():
    # 遍历ast_json文件夹，取出每一个工程文件夹的名字
    for project_dir_name in os.listdir(data_ast_json_dir_path):
        # 编译以后的抽象语法树的工程文件夹路径，现在还是文件夹级别，如"/home/xjj/AST-GNN/data/AST_json/project_name/"
        data_ast_json_project_dir_path = data_ast_json_dir_path + project_dir_name + "/"
        # 记录每个工程文件夹中保存的所有的节点有哪些，每个文件夹都是只使用一个，下次的文件夹时需要刷新内容。
        project_node_list = []
        # 遍历工程项目中的每一个文件
        for ast_json_file_name in os.listdir(data_ast_json_project_dir_path):
            # 抽象语法树文件的完全路径,如""/home/xjj/AST-GNN/data/AST_json/project_name/file_name.json"
            full_ast_json_path = data_ast_json_project_dir_path + ast_json_file_name
            # 为这个语法树文件删除前几行，因为生成的时候前面带上了一些不必要的信息
            with open(full_ast_json_path, 'r') as read_file, open(data_ast_json_project_dir_path + 'w.json', 'w+') as write_file:
                # 判断是否需要开始抄写的触发器
                flag = False
                for index, line in enumerate(read_file.readlines()):
                    # 如果已经需要开始记录了，开始抄写，把内容抄到w.json文件中
                    if flag:
                        write_file.write(line)
                        continue
                    # 如果发现已经到了这一行，那么说明从这里开始已经需要记录了。
                    if line.replace("\n", "") == "======= " + data_sol_source_dir_path + project_dir_name + "/" + ast_json_file_name.replace(".json", ".sol") + " =======":  # 会存在文件之间引用的情况，需要解析正确的json部分
                        flag = True
            # 删除原始的json文件，同时将刚刚生成的w.json文件转化为正确的名字。
            os.remove(full_ast_json_path)
            os.rename(data_ast_json_project_dir_path + 'w.json', full_ast_json_path)
            # 正式的开始读取json文件中的内容
            with open(full_ast_json_path, 'r') as ast_json:
                # 使用json的方式加载文件内容
                content = json.load(ast_json)
                # 将文件中的内容转化为图结构的数据，传入的内容有抽象语法树的内容，当前项目的所有节点列表，还有读入当前文件之前已经有多少个节点了，这个待会进去会变得，所以先记录下来。
                create_graph(content, project_node_list, len(project_node_list), data_sol_source_dir_path + project_dir_name + "/" + ast_json_file_name.replace(".json", ".sol"))
        # 循环当前项目中的所有节点，如果节点的类型已经存在了，直接记录下来，否则先创建key然后当作数组往里面添加。
        for node in project_node_list:
            if total_node_list.__contains__(node.node_type):
                total_node_list.get(node.node_type).append(node)
            else:
                total_node_list[node.node_type] = [node]
        # 如果需要打印树，那就打印。
        if config.show_plt:
            print_tree(project_node_list)
        # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
        built_corpus_bfs(project_node_list)
        built_corpus_dfs(project_node_list)
        if config.show_corpus_msg:
            w2v = Word2Vec.load(config.corpus_file_path)
            print(w2v.wv.vocab.keys())


# 根据传入的json内容生成一个简单的AST的树结构数据。
# content:json文件内容
# node_list:在当前工程文件夹中，已经记录的所有节点。
# node_list_len:在扫描当前文件之前，已经记录的所有节点的个数。
# source_file_name:传入当前源文件的名字，这样子可以再次去读取源文件中的内容，然后根据src的位置去获取当前节点代表的是哪一句语句。
def create_graph(content, node_list, node_list_len, source_file_name):
    # 保存当前源文件源代码的数组，相当于将源代码直接拆分为了['p', 'r', 'a', 'g', ...]这样子，后面直接从中间取出来就知道了节点代表的是哪条语句。
    src = []
    # 将内容进行循环遍历最终记录到上面的src的数组中。
    with open(source_file_name, 'r') as read_file:
        # 读取其中的字符
        for char in read_file.read():
            # 如果是\n那需要当作两个字符来处理，这个是为了适配用的。
            if char == "\n":
                src.append(char)
            src.append(char)
    # 创建队列，待会用来保存广度遍历里的东西
    queue = Queue(maxsize=0)
    # 根据内容创建节点，注意这里的id，需要时本身的id加上已经被记录的个数，否则到了下一份文件中，又从0开始就不好了。
    parent_node = create_new_node(content['id'] + node_list_len, content['nodeType'], None)
    # 将第一个节点的除了id和nodeType的所有属性，一起添加到节点上。
    for key in content.keys():
        # 如果不是id或者nodeType的属性，直接记录到attribute中，使用字典的形式。
        if not key == 'id' and not key == 'nodeType':
            parent_node.append_attribute(key, content[key])
            queue.put(content[key])
        # 这里代表了源代码的位置，可以直接使用下标从刚刚的源代码数组中切片获取。
        if key == "src":
            index_list = content["src"].split(":")
            src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
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
                node = create_new_node(q['id'] + node_list_len, q['nodeType'], parent_node)
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
                        index_list = q["src"].split(":")
                        src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
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
                        node = create_new_node(obj['id'] + node_list_len, obj['nodeType'], parent_node)
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
                                index_list = obj["src"].split(":")
                                src_content = src[int(index_list[0]): int(index_list[0]) + int(index_list[1])]
                                node.append_attribute("src_code", "".join(src_content))
                        # 先记录其属性，再记录这个节点。
                        node_list.append(node)
        # 如果是节点类型，说明需要更换父节点了。
        elif isinstance(q, Node):
            parent_node = q


# 传入一个队列中的内容，然后生成节点
# node_id:节点的id
# node_type:是节点的类型
# parent:当前这个节点的父节点是谁
def create_new_node(node_id, node_type, parent):
    node = Node(node_id, node_type, parent)
    return node
