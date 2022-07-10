import os
import json
from queue import Queue
import config
from gensim.models.word2vec import Word2Vec
from bean.Node import Node
from print_tree import print_tree
from built_corpus import built_corpus_bfs, built_corpus_dfs
from append_control_flow_information import append_control_flow_information

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
                    # 使用了新的判断条件，原先的通用性不是很好
                    if line.replace("\n", "").__contains__("======="):
                        flag = True
            # 删除原始的json文件，同时将刚刚生成的w.json文件转化为正确的名字。
            os.remove(full_ast_json_path)
            os.rename(data_ast_json_project_dir_path + 'w.json', full_ast_json_path)
            # 正式的开始读取json文件中的内容
            with open(full_ast_json_path, 'r') as ast_json:
                # 使用json的方式加载文件内容
                # 现在如果有问题，在一开始生成json的时候就已经被发现了，会直接被删除掉，而不是等到现在，所以不再需要进行try/catch。
                content = json.load(ast_json)
                # 使用分而治之的方法，把里面的id属性全部加上len(project_node_list)
                update_content(content, len(project_node_list))
                # 将文件中的内容转化为图结构的数据，传入的内容有抽象语法树的内容，当前项目的所有节点列表，还有读入当前文件之前已经有多少个节点了，这个待会进去会变得，所以先记录下来。
                create_graph(content, project_node_list, data_sol_source_dir_path + project_dir_name + "/" + ast_json_file_name.replace(".json", ".sol"))
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
        # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
        set_method_detail(project_node_dict)
        # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
        append_control_flow_information(project_node_list, project_node_dict)
        # 如果需要打印树，那就打印。
        if config.show_plt:
            print_tree(project_node_list)
        # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
        built_corpus_bfs(project_node_list)
        built_corpus_dfs(project_node_list)
        if config.show_corpus_msg:
            w2v = Word2Vec.load(config.corpus_file_path)
            print(w2v.wv.vocab.keys())
        # 循环当前项目中的所有节点，如果节点的类型已经存在了，直接记录下来，否则先创建key然后当作数组往里面添加。
        for node in project_node_list:
            if total_node_list.__contains__(node.node_type):
                total_node_list.get(node.node_type).append(node)
            else:
                total_node_list[node.node_type] = [node]
        # 将所有的节点类型放到了一个数组中进行排序，更加方便比对结果。
        node_types = []
        for key in total_node_list.keys():
            node_types.append(key)
        node_types.sort()
        print(len(total_node_list.keys()), node_types)


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


# 传入一个队列中的内容，然后生成节点
# node_id:节点的id
# node_type:是节点的类型
# parent:当前这个节点的父节点是谁
def create_new_node(node_id, node_type, parent):
    node = Node(node_id, node_type, parent)
    return node


# 设置函数的method_name等详细信息到attribute上。
def set_method_detail(project_node_dict):
    # 存在函数的情况下才调用这段代码
    if "FunctionDefinition" in project_node_dict.keys():
        # 循环所有的FunctionDefinition节点，找出其中的method_name作为新的属性。
        for node in project_node_dict['FunctionDefinition']:
            # 为了取出方法的名字，先获取start和end，然后去切分字符串。
            end = node.attribute['src_code'][0].index(")") + 1
            start_left_symbol = node.attribute['src_code'][0].index("(") + 1
            blank_index = node.attribute['src_code'][0].index(" ") + 1
            # 如果是先出现左括号，再出现空格，那就有问题。
            if start_left_symbol < blank_index:
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
