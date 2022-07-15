# coding=UTF-8
import os

# 四种运行的模式，是创建数据集create，训练train，还是预测valid，如果是truncated代表语言模型受损，需要重新训练。
run_mode = "create"
# 记录img、data、sol_source、ast_json、complete、raw的文件夹路径
img_dir_path = f"{os.getcwd()}/img"
data_dir_path = f"{os.getcwd()}/data"
data_sol_source_dir_path = f"{data_dir_path}/sol_source"
data_ast_json_dir_path = f"{data_dir_path}/AST_json"
data_complete_dir_path = f"{data_dir_path}/complete"
data_raw_dir_path = f"{data_dir_path}/raw"
# 标签文件的保存地址，这是加工之前的保存位置。这时候保存的内容比较粗糙,其中保存的格式是[{"0": 0}, {"1": 0}, {"2": 1}....]。
idx_to_label_file = f'{data_dir_path}/idx_to_label.json'
sol_to_label_file = f'{data_dir_path}/sol_to_label.json'
# compile_files中用到的版本匹配规则。
version_match_rule = "pragma solidity \\^?>?=?0\\.\\d{1,2}\\.\\d{1,2}"
# 在机器上的编译器文件的保存位置
compile_dir_path = "/home/xjj/.solc-select/artifacts/"
# 语料库文件是创建还是更新分别是create和update，如果是create就只是单纯为了获取corpus.txt，而update会用来生成三种训练文件。
create_corpus_mode = "update"
# 词库文件的保存位置。
corpus_file_path = f"{data_dir_path}/corpus_model.pkl"
corpus_txt_path = f"{data_dir_path}/corpus.txt"
# 词库文件当中，保存的每个单词的维度向量
encode_dim = 128
# 一共有三种模式:frozen,不删除之前的运行结果，而且运行结束的源文件会被移到success文件夹中。
frozen = "frozen"
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
# 最终生成的图片的宽度。
img_width = 12.0
# 最终生成的图片的高度。
img_height = 12.0
# 最终的分类数
classes = 2
# 批处理数量
batch_size = 64
# 学习率
learning_rate = 0.005
# 世代数量
epoch_size = 20
# 使用的设备
device = "cuda:1"
