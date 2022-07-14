# coding=UTF-8
# 是否要调用print_tree方法来显示图片
show_plt = False
# 是否要在print_tree方法中显示抽象语法树的边
show_AST_plt = True
# 是否要在print_tree方法中显示控制流图的边
show_CFG_plt = True
# 是否要在print_tree方法中忽略一些不重要的叶子节点
ignore_AST_some_list = False
# 设定好颜色集
color_dict = {"SourceUnit": "#ddd02f",
              "PragmaDirective": "#ddd02f",
              "ContractDefinition": "#ddd02f",
              "FunctionDefinition": "green",
              "Block": "orange",
              "ParameterList": "#32dd2f",
              "VariableDeclarationStatement": "yellow",
              "IfStatement": "skyblue",
              "WhileStatement": "skyblue",
              "DoWhileStatement": "skyblue",
              "ForStatement": "skyblue",
              "ExpressionStatement": "#2fddad",
              "Return": "red",
              "Break": "purple", "Continue": "purple"}
# 忽略不显示的节点类型。
ignore_list = ["ElementaryTypeName", "Assignment", "Literal", "VariableDeclaration", "Identifier", "UnaryOperation"]
# 词库文件的保存位置。
corpus_file_path = "./data/corpus_model.pkl"
# 词库文件当中，保存的每个单词的维度向量
encode_dim = 128
# 显示词库详细信息
show_corpus_msg = False
# 去匹配源文件当中的版本号
version_match_rule = "pragma solidity \\^?>?=?0\\.\\d{1,2}\\.\\d{1,2}"
# 最终生成的图片的宽度。
img_width = 12.0
# 最终生成的图片的高度。
img_height = 12.0
# 是否显示编译sol的命令语句
print_compile_cmd = True
# 在机器上的编译器文件的保存位置
compile_dir_path = "/home/xjj/.solc-select/artifacts/"
# 是否需要显示所有的节点的类型。
need_show_total_node_node_type = True
# 用来控制训练的时候使用的设备
device = "cuda:1"
# 一共有三种模式:1.delete,会在运行前先删除之前的运行结果。2.frozen,不删除之前的运行结果，而且运行结束的源文件会被移到success文件夹中。
frozen = "frozen"
# 训练模型的分类数。
classes = 2
# 训练世代的总数量
epoch_size = 10
# 训练的时候的学习率
learning_rate = 0.005
# 训练时候的batch大小
batch_size = 64
