# coding=UTF-8
import os
import argparse
import datetime
import torch

# 默认会先加载config配置文件夹，然后设定好程序运行的配置。
parser = argparse.ArgumentParser(description='参数表')
# create:创建数据集的时候用的
# train:训练模式
# predict:预测模式,后面这里可能要开两个预测的分支。
# truncated:语言模型受损，需要重新训练。
parser.add_argument('--run_mode', type=str,
                    help="运行模式:\n"
                         "1.create:创建数据集的时候用的。\n"
                         "2.train:训练模式(这个是文件级别的)。\n"
                         "3.predict:预测模式。\n"
                         "4.truncated:语言模型受损，需要重新训练。\n"
                         "5.line_classification_train:行级别的漏洞检测。\n"
                         "6.contract_classification_train:合约级别的漏洞检测。\n")
# create_corpus_txt:仅仅创建语料库文件。
# generate_all: 生成所有的向量文件。
# 如果run_mode已经进行了训练阶段或者预测阶段，建议这里直接设置为无效值。
parser.add_argument('--create_corpus_mode', type=str,
                    help="创建文件的模式:\n"
                         "1.create_corpus_txt:仅仅创建语料库文件。\n"
                         "2.generate_all: 生成所有的向量文件。\n")
parser.add_argument('--train_mode', type=str,
                    help="针对创建文件的模式一起使用的，如果创建文件的模式是generate_all"
                         "那么这里应该标注是合约级别还是行级别，因为built_vector_dataset的时候需要根据不同的任务类型，读取不一样的json文件")
# data_dir_name:数据文件夹的名字，这样子就可以在一个项目里面多次运行，只要多创建data目录就行。
parser.add_argument('--data_dir_name', type=str,
                    help="数据文件夹的名字，为了可以多进程启动运行:\n")
# attack_type_name:专门要操作的漏洞的类型的名字。
parser.add_argument('--attack_type_name', type=str,
                    help="本次要操作的漏洞的类型，专门只操作这种漏洞。")
# create_code_snippet:创建合约的片段的触发器
parser.add_argument('--create_code_snippet', action='store_true',
                    help="本次操作是否是用来创建合约的片段的")
parser.add_argument('--data_augmentation', action='store_true',
                    help="本次操作是否是用来拓展数据集的")
parser.add_argument('--gpu_id', default=0, type=int, help="本次操作的gpu用哪个")
# 下面更新config配置
args = parser.parse_args()
# ========================= 运行模式 =========================
# create:创建数据集的时候用的
# train:训练模式
# predict:预测模式
# truncated:语言模型受损，需要重新训练。
run_mode = args.run_mode
# create_corpus_txt:仅仅创建语料库文件。
# generate_all: 生成所有的向量文件
create_corpus_mode = args.create_corpus_mode
# 如果create_corpus_mode的模式是generate_all,这里会影响到built_vector_dataset中读取的json文件是哪些。
train_mode = args.train_mode
# frozen,不删除之前的运行结果，而且运行结束的源文件会被移到success文件夹中。
# not frozen:运行结束的话，sol文件也一直放在原始的sol_source文件中，方便测试
frozen = "frozen"
# 专门操作的漏洞类型。
attack_type_name = args.attack_type_name
# 创建合约的片段的触发器
create_code_snippet = args.create_code_snippet
# 判断当前运行程序的目的是不是用来数据增强的
data_augmentation = args.data_augmentation
# 本次使用的gpu_id
gpu_id = args.gpu_id
# ========================= 运行模式 =========================
# ========================= 文件夹路径 =========================
# 记录img、data、sol_source、ast_json、complete、raw的文件夹路径
root_dir = f"{os.getcwd()}"
data_dir_path = f"{root_dir}/{args.data_dir_name}"
img_dir_path = f"{data_dir_path}/img"
data_sol_source_dir_path = f"{data_dir_path}/sol_source"
data_ast_json_dir_path = f"{data_dir_path}/AST_json"
data_complete_dir_path = f"{data_dir_path}/complete"
data_raw_dir_path = f"{data_dir_path}/raw"
data_process_dir_path = f"{data_dir_path}/processed"
# 片段代码库文件
code_snippet_library_path = f"{root_dir}/code_snippet_library"
# 文件hash值的保存位置。
hash_to_file = f"{data_dir_path}/hash_to_file.json"
# 标签文件的保存地址，这是加工之前的保存位置。这时候保存的内容比较粗糙,其中保存的格式是{"0": 0, "1": 0, "2": 1}。
idx_to_label_file = f'{data_dir_path}/idx_to_label.json'
# 缺乏版本号码的保存地址
absent_version_cmd_file = f"{data_dir_path}/absent_version_cmd.txt"
# 没有漏洞的文件夹
no_attack_fold = f'{data_dir_path}/attack/no_attack_fold/'
# 重入攻击的文件夹
reentry_attack_fold = f'{data_dir_path}/attack/reentry_attack_fold/'
# 时间戳攻击的文件夹
timestamp_attack_fold = f"{data_dir_path}/attack/timestamp_attack_fold/"
# 溢出漏洞的文件夹
arithmetic_attack_fold = f"{data_dir_path}/attack/arithmetic_attack/"
# 疑似重入攻击的文件夹
suspected_reentry_attack_fold = f'{data_dir_path}/attack/suspected_reentry_attack_fold/'
# 疑似时间戳攻击的文件夹
suspected_timestamp_attack_fold = f"{data_dir_path}/attack/suspected_timestamp_attack_fold/"
# 疑似溢出漏洞的文件夹
suspected_arithmetic_attack_fold = f"{data_dir_path}/attack/suspected_arithmetic_attack/"
# 运行过程中出错的保存文件夹
error_file_fold = f"{data_dir_path}/error/"
# 等待检测的文件夹,里面会包含所有预测时候用到的文件夹
wait_predict_fold = f"{data_dir_path}/wait_predict"
# 预测的时候保存源代码的文件夹
wait_predict_sol_source_fold = f"{wait_predict_fold}/sol_source"
# 预测时候保存源代码编译后的json文件的文件夹
wait_predict_ast_json_fold = f"{wait_predict_fold}/AST_json"
# 保存向量化文件的文件夹
wait_predict_data_raw_dir_path = f"{wait_predict_fold}/raw"
# ========================= 文件夹路径 =========================
# ========================= 编译配置 =========================
# compile_files中用到的版本匹配规则,仅仅是用来判断当前行是否带有版本信息
version_match_rule = r"pragma solidity ([><=^]* ?[\d.]{5,6} ?)+;"
# 在机器上的编译器文件的保存位置
compile_dir_path = "/data/space_station/.solc-select/artifacts/"
# 版本表
versions = ["0.4.0", "0.4.1", "0.4.2", "0.4.3", "0.4.4", "0.4.5", "0.4.6", "0.4.7", "0.4.8", "0.4.9", "0.4.10", "0.4.11", "0.4.12", "0.4.13", "0.4.14", "0.4.15", "0.4.16", "0.4.17", "0.4.18", "0.4.19", "0.4.20", "0.4.21", "0.4.22", "0.4.23", "0.4.24", "0.4.25", "0.4.26",
            "0.5.0", "0.5.1", "0.5.2", "0.5.3", "0.5.4", "0.5.5", "0.5.6", "0.5.7", "0.5.8", "0.5.9", "0.5.10", "0.5.11", "0.5.12", "0.5.13", "0.5.14", "0.5.15", "0.5.16", "0.5.17",
            "0.6.0", "0.6.1", "0.6.2", "0.6.3", "0.6.4", "0.6.5", "0.6.6", "0.6.7", "0.6.8", "0.6.9", "0.6.10", "0.6.11", "0.6.12",
            "0.7.0", "0.7.1", "0.7.2", "0.7.3", "0.7.4", "0.7.5", "0.7.6",
            "0.8.0", "0.8.1", "0.8.2", "0.8.3", "0.8.4", "0.8.5", "0.8.6", "0.8.7", "0.8.8", "0.8.9", "0.8.10", "0.8.11", "0.8.12", "0.8.13", "0.8.14", "0.8.15"]
# ========================= 编译配置 =========================
# ========================= 生成语言库配置 =========================
# 词库文件的保存位置。
corpus_file_path = f"{data_dir_path}/corpus_model.pkl"
corpus_txt_path = f"{data_dir_path}/corpus.txt"
# 词库文件当中，保存的每个单词的维度向量
encode_dim = 300
# 用来分割用的单词。
split_word = "(●'◡'●)"
# ========================= 生成语言库配置 =========================
# ========================= 图可视化配置 =========================
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
# ========================= 图可视化配置 =========================
# ========================= 模型和度量标准配置 =========================
device = torch.device(f"cuda:{gpu_id}")
# 使用的gpu设备
average_num = 20
# 开几个线程进行计算。
thread_num = 2
# 配置环境,设定当前程序可见GPU只有这几个,这样子就可以设定多GPU用哪几块。
os.environ['CUDA_VISIBLE_DEVICES'] = "0,1"
# 多线程加载数据
num_workers = 0
# 最终的分类数
classes = 3
# 批处理数量
batch_size = 32
# 学习率
learning_rate = 0.005
# 学习率更新epoch
learning_change_epoch = 10
# 学习率更新的倍率
learning_change_gamma = 0.75
# 梯度消失的阈值
disappear_threshold = 0.01
# 异常损失的绝对值
exception_for_graph_abs = 50
# 异常损失对图数量比例
exception_for_graph_per = 1
# 防止梯度消失
weight_decay = 0.005
# dropout的概率
dropout_pro = 0.1
# 世代数量
epoch_size = 50
# K折交叉验证的数量。
k_folds = 10
# 上下文共同计算的系数
coefficient = [0.5, 1, 0.5]
# 模型文件的保存位置
model_data_dir = f"{data_dir_path}/model"
# 保存tensor board文件的位置
tensor_board_position = f"{data_dir_path}/tensorboard_logs"
# 计算度量标准的时候使用的参数
beta = 1
epsilon = 1e-8
# 阈值调优的时候使用的总长度，到时候计算的总类最大也只会是这个值。
threshold_max_classes = 2500
# 为tensor board创建的文件名字前缀。
start_time = datetime.datetime.now()
# 攻击的最佳阈值
threshold = 0
# 测试集的占比。
test_dataset_percent = 0.3
# 用问题类型找到对应的下标。
attack_list = ["reentry", "timestamp", "arithmetic"]
# ========================= 模型和度量标准配置 =========================
# ========================= 漏洞建模配置 =========================
# 构建数据流的时候最大的耐心时间，如果时间到了，就停止当前文件，因为没有必要，肯定是里面路径太多爆炸了，这里是以秒为单位的。
create_data_flow_max_time = 40
# 给文件进行重入攻击漏洞查询的最大时间，如果时间到了还没有找到漏洞也没有结束，那就说明是路径太多太爆炸了，提前退出，单位是秒。
make_reentry_attack_label_max_time = 40
# 给文件进行时间戳漏洞查询的最大时间，如果时间到了还没有找到漏洞也没有结束，那就说明是路径太多太爆炸了，提前退出，单位是秒。
make_timestamp_attack_label_max_time = 40
# 给文件进行算数溢出漏洞查询的最大时间，如果时间到了还没有找到漏洞也没有结束，那就说明是路径太多太爆炸了，提前退出，单位是秒。
make_arithmetic_attack_label_max_time = 40
# ========================= 漏洞建模配置 =========================
# ========================= 输出配置 =========================
tqdm_ncols = 100
table_width = 120
# ========================= 输出配置 =========================
# ========================= 代码片段的配置 ==============================
# 每一份的clean文件用来创建多少个代码片段。
code_snippet_number = 50
# ========================= 代码片段的配置 ==============================
