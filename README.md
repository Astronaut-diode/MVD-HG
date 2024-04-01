# MVD-HG

## Introduce

为Smart Contract提取以AST、CFG、DFG为基础的异构图，使用图神经网络进行多粒度的分类，实现行级别以及合约级别的漏洞检测任务。

总体框架图如下所示：

![AST-GNN](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/ecaefc9a-6d89-4c72-9f33-2675a1687baa)

得到的异构图案例如下所示：

![AST-GNN1](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/1bd8db14-315a-4611-a178-4e15c4a30da3)

## Usage

在dataset.zip中已经压缩了28组数据集。分别是7种漏洞类型，每组漏洞类型都分为原始合约级别，增强以后合约级别、原始行级别、增强后行级别。每个文件夹中都存有对应的cmd命令，可用于运行、测试。

## Expermental Results

数据集组成

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/77d0cb79-a74b-42bf-947a-e82b59480f13)

原始合约级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/5ce6a939-0feb-4f85-a037-bf330c9b1bb1)

原始行级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/4e21da8f-4368-4d34-aa2b-27640bc6f987)

使用数据增强以后的合约级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/a8d8f1c5-128d-4cf4-b988-c7c24da8aca9)

使用数据增强以后的行级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/705ed97f-84f5-49cc-baad-7b97f8f52577)

不同类型组成异构图的消融实验结果(增强以后的数据集)。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/26496d3e-9d75-4270-baf4-fa1820b844d0)

进行参数实验以后得到的结果。

![图3-4 参数实验](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/ff3938ef-0f9f-47a5-884b-257c05cd6ecf)

## Project Architecture

``` shell
root@iZbp1dlnrh61z7i0vvirdpZ:~/code/MVD-HG# tree 
.
├── append_control_flow_information.py  # 为提取出的节点增加控制流信息。
├── append_data_flow_information.py  # 为提取出的节点增加数据流信息。
├── append_method_message_by_dict.py  # 为提取出的节点设置函数信息、所属Contract等。
├── bash  # 一些实验时快速启动的脚本文件。
│   ├── go.sh
│   ├── 启动三次运行.vbs
│   ├── 启动虚拟环境.vbs
│   ├── 监视程序运行情况.vbs
│   ├── 直接启动tensorboard.vbs
│   └── 脚本说明.txt
├── bean
│   └── Node.py  # 节点类。
├── built_corpus.py  # 构建语料库文件的txt和pkl模型文件。
├── built_vector_dataset.py  # 根据节点信息构建出持久化的本地向量化文件
├── classification_of_documents.py  # 将所有有漏洞的文件进行分门别类地存放起来，方便下次检验。
├── compile_files.py  # 编译智能合约源代码。
├── config.py  # 配置文件。
├── contract_classification  # 合约级别漏洞检测走的流程分支。
│   ├── contract_classification_dataset.py  # 加载的数据集格式。
│   ├── contract_classification_model.py  # 使用的模型。
│   └── contract_classification_train.py  # 训练过程。
├── create_code_snippet.py  
├── data  # 存放实验时使用的数据源，以及各种生成的结果文件等。
│   ├── AST_json  # 编译后的结果，保存json文件。
│   │   └── contract1_0xfD904a11fEC111F353ec8A5C9af203c59391dECA_Bank
│   │       └── 0xfD904a11fEC111F353ec8A5C9af203c59391dECA_Bank.sol
│   ├── attack  # 之前提到的有漏洞的文件进行分门别类保存的地方。
│   │   ├── arithmetic_attack
│   │   │   └── contract1_0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal
│   │   │       └── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal.json
│   │   ├── dangerous_delegate_call_attack
│   │   │   └── contract1_0xfef736cfa3b884669a4e0efd6a081250cce228e7_Bob
│   │   │       └── 0xfef736cfa3b884669a4e0efd6a081250cce228e7_Bob.json
│   │   ├── reentry_attack_fold
│   │   │   └── contract1_0x064d0c8d8100ba8c57a63d75a5fb8ede18d7fe4b_QSHUCOIN
│   │   │       └── 0x064d0c8d8100ba8c57a63d75a5fb8ede18d7fe4b_QSHUCOIN.json
│   │   └── timestamp_attack_fold
│   │       └── contract1_0xF9d3402066E3a483f4ca7abFa78DEC61635E561f_PreCrowdsale
│   │           └── 0xF9d3402066E3a483f4ca7abFa78DEC61635E561f_PreCrowdsale.json
│   ├── complete  # 当还是create_corpus_txt的时候，这里保存所有被处理过的文件，但是之后会被移送回sol_source。generate_all则不会移送回去。
│   │   └── contract1_0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket
│   │       └── 0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket.sol
│   ├── corpus_model.pkl  # 语言模型。
│   ├── corpus.txt  # 语言库。
│   ├── error  # 如果编译出错，或者执行流程中出错的文件。
│   │   └── contract1_0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt
│   │       └── 0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt.sol
│   ├── idx_to_label.json  # 通过自己的漏洞模型，给出的漏洞标签。
│   ├── img  # 保存图形化以后的结果。
│   │   └── contract1_0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt
│   │       └── 0xc9Fa8308cd98A6144450D68B6C546062dbBD984e_CrowdsaleTokenExt.svg
│   ├── log  # 日志文件
│   ├── processed  # 预处理以后形成的真正的数据集。
│   │   ├── graph_train.pt
│   │   ├── pre_filter.pt
│   │   └── pre_transform.pt
│   ├── raw  # 原始的向量文件。
│   │   └── contract1_0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal  # 每一个文件夹下面都会有三份边文件和一个节点文件。
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_ast_edge.json
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_cfg_edge.json
│   │       ├── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_dfg_edge.json
│   │       └── 0xb725213a735ae34e1903d1971700dd7f0858f212_BankofIsreal_node.json
│   ├── sol_source  # 原始文件夹，要处理的文件都放在这里面。
│   │   └── contract1_0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket
│   │       └── 0xfc9ec868f4c8c586d1bb7586870908cca53d5f38_KittyItemMarket.sol
│   └── tensorboard_logs  # 使用tensorboard以后保存的文件夹。
│       └── events.out.tfevents.1658990929.dell-PowerEdge-T640.126902.0
├── data_process.py  # 额外的数据处理文件。
├── dataset.py  # 构建数据集的文件。
├── dataset.zip  # 实验使用的数据集。
├── hash_code.py  # 可以过滤重复的文件，提取每个文件的hash结果。
├── line_classification  # 行级别漏洞检测的流程分支。
│   ├── line_classification_dataset.py  # 加载的数据集格式。
│   ├── line_classification_model.py  # 使用的模型。
│   └── line_classification_train.py  # 训练过程。
├── load_model_to_predict.py  # 加载模型用于训练。
├── main.py  # 主文件。
├── make_arithmetic_attack_label.py  # 使用专家规则，求出arithmetic的标签文件（已弃用）。
├── make_reentry_attack_label.py   # 使用专家规则，求出reentry的标签文件（已弃用）。
├── make_timestamp_attack_label.py   # 使用专家规则，求出timestamp的标签文件（已弃用）。
├── merge.py  
├── metric.py  # 度量文件，在这里会计算多种的度量标准。
├── model.py  # 网络模型（已弃用）。
├── print_tree.py  # 将异构图按照树形打印出来，可视化出来。
├── read_compile.py  # 读取编译完的结果，然后生成图结构的内存数据。
├── README.md
├── remove_blank.py  # 删除源文件中的空行。
├── remove_comments.py  # 删除源文件中的注释。
├── train.py  # 训练文件（已弃用）。
└── utils.py  # 一些通用的工具函数。
```

## Maintainers

徐敬杰

[@Astronaut-diode](https://github.com/Astronaut-diode) 

浙江工业大学 软件工程专业硕士在读

邮箱地址:925791559@qq.com
