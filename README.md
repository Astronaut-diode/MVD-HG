# AST-GNN
图神经网络训练Solidity的抽象语法树

### 项目结构

``` sh
(remote_virtue_env) xjj@dell-PowerEdge-T640:~/AST-GNN$ tree
.
├── append_control_flow_information.py		# 给文件上的节点增加控制流信息
├── append_method_message_by_dict.py		# 给文件上的节点增加详细信息
├── bean
│   ├── Node.py		# 项目中用到的类
├── built_corpus.py		# 构建语料库文件的txt和pkl模型文件
├── built_vector_dataset.py		# 根据节点信息构建出持久化的本地向量化文件
├── compile_files.py		# 编译sol文件得到json文件
├── config.py		# 配置文件
├── data		# 数据文件夹，其中AST_json、complete、img、sol_source、raw都是核心文件夹，每个保存的都是原始的工程结构。
│   ├── AST_json
│   │   └── 0x9711ddc5a40318dd7fe63f44682e8748f54d60dc
│   │       └── SIGMA.json
│   ├── complete
│   │   └── 0x9711ddc5a40318dd7fe63f44682e8748f54d60dc
│   │       └── SIGMA.sol
│   ├── corpus_model.pkl		# 语言库模型文件
│   ├── corpus.txt				# 语言库的txt文件，用来构建模型的原始文件。
│   ├── idx_to_label.json		# 标签文件。
│   ├── img
│   │   └── 0x9711ddc5a40318dd7fe63f44682e8748f54d60dc
│   │       └── 2022-07-17 09-55-15-SIGMA.png
│   ├── processed			# 根据raw构建出来的数据集。
│   │   ├── ast_graph_train.pt
│   │   ├── cfg_graph_train.pt
│   │   ├── pre_filter.pt
│   │   └── pre_transform.pt
│   ├── raw
│   │   └── 0x9711ddc5a40318dd7fe63f44682e8748f54d60dc
│   │       ├── SIGMA_ast_edge.json
│   │       ├── SIGMA_cfg_edge.json
│   │       └── SIGMA_node.json
│   ├── sol_source
│   │   └── 0x9711ddc5a40318dd7fe63f44682e8748f54d60dc
│   │       └── SIGMA.sol
├── dataset.py		# 构建数据集的文件
├── main.py			# 主文件
├── model.py		# GNN模型文件
├── print_tree.py	# 打印图结构信息以及保存图片的文件
├── read_compile.py	# 读取编译以后的json文件，转化为图信息的文件
├── remove_comments.py	# 删除注释信息你文件
├── train.py		# 训练文件
└── utils.py		# 工具文件
```

