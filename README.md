# AST-GNN
图神经网络训练Solidity的抽象语法树

### 项目结构

``` shell
.
├── append_control_flow_information.py# 给文件上的节点增加控制流信息
├── append_data_flow_information.py# 增加数据流信息
├── append_method_message_by_dict.py# 给文件上的节点增加详细信息
├── bash# 存放所有脚本文件的位置
│   ├── go.sh
│   ├── 直接启动tensorboard.vbs
│   ├── 脚本说明.txt
│   ├── 启动三次运行.vbs
│   ├── 监视程序运行情况.vbs
│   └── 启动虚拟环境.vbs
├── bean
│   ├── Node.py# 项目中用到的类
│   └── __pycache__
│       └── Node.cpython-38.pyc
├── built_corpus.py# 构建语料库文件的txt和pkl模型文件
├── built_vector_dataset.py# 根据节点信息构建出持久化的本地向量化文件
├── classification_of_documents.py# 将所有有漏洞的文件进行分门别类地存放起来，方便下次检验。
├── compile_files.py# 编译源代码的文件
├── config.py# 配置文件
├── data
│   ├── AST_json# 编译后的结果，保存json文件
│   │   └── contract1_0xfD904a11fEC111F353ec8A5C9af203c59391dECA_Bank
│   │       └── 0xfD904a11fEC111F353ec8A5C9af203c59391dECA_Bank.sol
│   ├── attack# 之前提到的有漏洞的文件进行分门别类保存的地方。
│   │   ├── arithmetic_attack
│   │   │   └── contract1_0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal
│   │   │       └── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal.json
│   │   ├── dangerous_delegate_call_attack
│   │   │   └── contract1_0xfef736cfa3b884669a4e0efd6a081250cce228e7_Bob
│   │   │       └── 0xfef736cfa3b884669a4e0efd6a081250cce228e7_Bob.json
│   │   ├── reentry_attack_fold
│   │   │   └── contract1_0x064d0c8d8100ba8c57a63d75a5fb8ede18d7fe4b_QSHUCOIN
│   │   │       └── 0x064d0c8d8100ba8c57a63d75a5fb8ede18d7fe4b_QSHUCOIN.json
│   │   └── timestamp_attack_fold
│   │       └── contract1_0xF9d3402066E3a483f4ca7abFa78DEC61635E561f_PreCrowdsale
│   │           └── 0xF9d3402066E3a483f4ca7abFa78DEC61635E561f_PreCrowdsale.json
│   ├── complete# 当还是create_corpus_txt的时候，这里保存所有被处理过的文件，但是之后会被移送回sol_source。generate_all则不会移送回去。
│   │   └── contract1_0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket
│   │       └── 0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket.sol
│   ├── corpus_model.pkl# 语言模型。
│   ├── corpus.txt# 语言库
│   ├── error# 如果编译出错，或者执行流程中出错的文件。
│   │   └── contract1_0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt
│   │       └── 0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt.sol
│   ├── idx_to_label.json# 通过自己的漏洞模型，给出的漏洞标签
│   ├── img# 保存图形化以后的结果。
│   │   └── contract1_0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt
│   │       └── 0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt.svg
│   ├── log# 日志文件
│   ├── processed# 预处理以后形成的真正的数据集。
│   │   ├── graph_train.pt
│   │   ├── pre_filter.pt
│   │   └── pre_transform.pt
│   ├── raw# 原始的向量文件。
│   │   └── contract1_0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal# 每一个文件夹下面都会有三份边文件和一个节点文件。
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_ast_edge.json
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_cfg_edge.json
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_dfg_edge.json
│   │       └── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_node.json
│   ├── sol_source# 原始文件夹，要处理的文件都放在这里面。
│   │   └── contract1_0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket
│   │       └── 0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket.sol
│   └── tensorboard_logs# 使用tensorboard以后保存的文件夹
│       └── events.out.tfevents.1658990929.dell-PowerEdge-T640.126902.0
├── dataset.py# 构建数据集的文件
├── gets_command_line_arguments.py# 根据命令行获取执行的参数
├── main.py# 主文件
├── make_tag.py# 给原始文件打上标签。
├── metric.py# 度量文件，在这里会计算多种的度量标准。
├── model.py# 模型文件，写网络模型的地方。
├── print_tree.py# 图形化源代码的抽象语法树等。
├── read_compile.py# 读取编译完的结果，然后生成图结构的内存数据。
├── README.md
├── remove_comments.py# 删除所有的注释
├── train.py# 训练文件
└── utils.py# 工具包
```

