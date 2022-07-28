# coding=UTF-8
import os

# create:创建数据集的时候用的
# train:训练模式
# valid:预测模式
# truncated:语言模型受损，需要重新训练。
run_mode = "create"
# create_corpus_txt:仅仅创建语料库文件。
# generate_all: 生成所有的向量文件
create_corpus_mode = "generate_all"
# frozen,不删除之前的运行结果，而且运行结束的源文件会被移到success文件夹中。
frozen = "frozen"
# 记录img、data、sol_source、ast_json、complete、raw的文件夹路径
data_dir_path = f"{os.getcwd()}/data"
img_dir_path = f"{data_dir_path}/img"
data_sol_source_dir_path = f"{data_dir_path}/sol_source"
data_ast_json_dir_path = f"{data_dir_path}/AST_json"
data_complete_dir_path = f"{data_dir_path}/complete"
data_raw_dir_path = f"{data_dir_path}/raw"
# 保存tensorboard文件的位置
tensor_board_position = f"{data_dir_path}/tensorboard_logs"
# 标签文件的保存地址，这是加工之前的保存位置。这时候保存的内容比较粗糙,其中保存的格式是{"0": 0, "1": 0, "2": 1}。
idx_to_label_file = f'{data_dir_path}/idx_to_label.json'
# 重入攻击的文件夹
reentry_attack_fold = f'{data_dir_path}/attack/reentry_attack_fold/'
# 时间戳攻击的文件夹
timestamp_attack_fold = f"{data_dir_path}/attack/timestamp_attack_fold/"
# 溢出漏洞的文件夹
arithmetic_attack_fold = f"{data_dir_path}/attack/arithmetic_attack/"
# 危险调用漏洞的文件啊及
dangerous_delegate_call_attack_fold = f"{data_dir_path}/attack/dangerous_delegate_call_attack/"
# 运行过程中出错的保存文件夹
error_file_fold = f"{data_dir_path}/error/"
# compile_files中用到的版本匹配规则,仅仅是用来判断当前行是否带有版本信息
version_match_rule = r"pragma solidity ([><=^]* ?[\d.]{5,6} ?)+;"
# 在机器上的编译器文件的保存位置
compile_dir_path = "/home/xjj/.solc-select/artifacts/"
# 词库文件的保存位置。
corpus_file_path = f"{data_dir_path}/corpus_model.pkl"
corpus_txt_path = f"{data_dir_path}/corpus.txt"
# 词库文件当中，保存的每个单词的维度向量
encode_dim = 128
# 是否要调用print_tree方法来显示图片
show_plt = False
# 是否要在print_tree方法中显示抽象语法树的边
show_AST_plt = True
# 是否要在print_tree方法中显示控制流图的边
show_CFG_plt = True
# 是否要再print_tree方法中显示数据流图的边
show_DFG_plt = True
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
# 最终的分类数
classes = 4
# 批处理数量
batch_size = 64
# 学习率
learning_rate = 0.005
# 世代数量
epoch_size = 20
# 使用的设备
device = "cuda:1"
# 验证的时候使用的阈值。
valid_threshold = 0.5
# 版本表
versions = ["0.4.0", "0.4.1", "0.4.2", "0.4.3", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.4.9", "0.4.10", "0.4.11", "0.4.12", "0.4.13", "0.4.14", "0.4.15", "0.4.16", "0.4.17", "0.4.18", "0.4.19", "0.4.20", "0.4.21", "0.4.22", "0.4.23", "0.4.24", "0.4.25", "0.4.26",
            "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.5.4", "0.5.5", "0.5.6", "0.5.7", "0.5.8", "0.5.9", "0.5.10", "0.5.11", "0.5.12", "0.5.13", "0.5.14", "0.5.15", "0.5.16", "0.5.17",
            "0.6.0", "0.6.1", "0.6.2", "0.6.3", "0.6.4", "0.6.5", "0.6.6", "0.6.7", "0.6.8", "0.6.9", "0.6.10", "0.6.11", "0.6.12",
            "0.7.0", "0.7.1", "0.7.2", "0.7.3", "0.7.4", "0.7.5", "0.7.6",
            "0.8.0", "0.8.1", "0.8.2", "0.8.3", "0.8.4", "0.8.5", "0.8.6", "0.8.7", "0.8.8", "0.8.9", "0.8.10", "0.8.11", "0.8.12", "0.8.13", "0.8.14", "0.8.15"]
