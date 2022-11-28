from gensim.models.word2vec import Word2Vec
from remove_comments import remove_comments
from compile_files import compile_files
from read_compile import read_compile
from append_method_message_by_dict import append_method_message_by_dict
from append_control_flow_information import append_control_flow_information
from append_data_flow_information import append_data_flow_information
from built_corpus import built_corpus_bfs, built_corpus_dfs
from built_vector_dataset import built_vector_dataset
from print_tree import generate_svg
from torch_geometric.data import Data
from dataset import ASTGNNDataset
from model import ASTGNNModel
import numpy as np
import utils
import config
import torch
import os
import re
from tqdm import tqdm


def load_model_to_predict():
    # 挑选出最优秀的模型
    max_score = 0
    max_mode_file = os.listdir(config.model_data_dir)[0]
    for model_file in os.listdir(config.model_data_dir):
        query = re.search("\[(.*?)\]", model_file, re.I | re.M)
        if float(query.group(1)) > max_score:
            max_score = float(query.group(1))
            max_mode_file = model_file
    model = ASTGNNModel()
    # 加载原始保存的参数
    model_params_dict = torch.load(os.path.join(config.model_data_dir, max_mode_file))
    best_threshold = model_params_dict["best_threshold"]
    # 将加载的参数添加到模型当中去
    model.load_state_dict(model_params_dict["model_params"])
    # 加载词向量的模型,在这里加载是为了服务所有需要被检验的文件。
    word2vec_model = Word2Vec.load(config.corpus_file_path).wv
    dangerous_count = 0
    safe_count = 0
    exception_count = 0
    # 遍历wait_pre下的
    for project_name in tqdm(os.listdir(config.wait_predict_sol_source_fold)):
        # wait_predict/sol_source/下面所有的工程文件夹
        sol_source_project_dir_path = f'{config.wait_predict_sol_source_fold}/{project_name}'
        ast_json_project_dir_path = f'{config.wait_predict_ast_json_fold}/{project_name}'
        # 删除源文件中的注释
        remove_comments(data_sol_source_project_dir_path=sol_source_project_dir_path)
        # 编译sol_source下工程文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
        compile_files(data_sol_source_project_dir_path=sol_source_project_dir_path, data_ast_json_project_dir_path=ast_json_project_dir_path)
        # 遍历这个json文件的文件夹，取出其中所有的子文件夹
        for now_dir, child_dirs, child_files in os.walk(ast_json_project_dir_path):
            # 遍历工程项目中的每一个文件
            for ast_json_file_name in child_files:
                try:
                    # 读取刚刚记录下来的抽象语法树的json文件
                    project_node_list, project_node_dict = read_compile(now_dir=now_dir, ast_json_file_name=ast_json_file_name)
                    # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
                    append_method_message_by_dict(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
                    append_control_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 根据内存中的数据，设定图的数据流。
                    append_data_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    try:
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)
                    except Exception as e:
                        utils.error(f"{e}需要先更新词表")
                        # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
                        built_corpus_bfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                        built_corpus_dfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                        # 加载词向量的模型,在这里加载是因为原始的文本库模型文件可能被修改了，但是读入的是原始的。
                        word2vec_model = Word2Vec.load(config.corpus_file_path).wv
                        # 创建数据集
                        built_vector_dataset(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)
                    # 打印树的样子。
                    generate_svg(project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 获取对应raw工程文件夹下的原始文件名_node.json文件中的内容。
                    x = ASTGNNDataset.get_x(os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    # 获取抽象语法树边的信息
                    ast_edge_index = ASTGNNDataset.get_ast_edge(os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    # 创建边的属性
                    ast_edge_attr = torch.zeros(ast_edge_index.shape[1])
                    cfg_edge_index = ASTGNNDataset.get_cfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    cfg_edge_attr = torch.zeros(cfg_edge_index.shape[1]) + 1
                    dfg_edge_index = ASTGNNDataset.get_dfg_edge(os.path.join(now_dir.replace("AST_json", "raw"), ast_json_file_name.replace(".json", "")))
                    dfg_edge_attr = torch.zeros(dfg_edge_index.shape[1]) + 2
                    # 将上面三份内容一起使用，用来构造一份数据集。
                    edge_index = torch.cat((ast_edge_index, cfg_edge_index, dfg_edge_index), dim=1)
                    edge_attr = torch.cat((ast_edge_attr, cfg_edge_attr, dfg_edge_attr))
                    # 通过节点属性，边连接情况，边的属性，还有标签一起构建数据集。
                    predict_data = Data(x=x, edge_index=edge_index, edge_attr=edge_attr, batch=torch.as_tensor(data=np.array(np.array([0] * x.shape[0], dtype=np.int64))))
                    predict = model(predict_data).item()
                    utils.tip(predict)
                    if predict < best_threshold[0].item():
                        utils.success(f"{ast_json_file_name}中并不存在{config.attack_type_name}类型的漏洞")
                        safe_count += 1
                    else:
                        utils.success(f"{ast_json_file_name}中存在{config.attack_type_name}类型的漏洞")
                        dangerous_count += 1
                except Exception as e:
                    utils.success(f"{ast_json_file_name}执行过程中出现异常了{e}")
                    exception_count += 1
    utils.tip(f"有漏洞的一共有{dangerous_count}")
    utils.tip(f"无漏洞的一共有{safe_count}")
    utils.tip(f"有异常的一共有{exception_count}")
