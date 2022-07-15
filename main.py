from remove_comments import remove_comments
from compile_files import compile_files
from read_compile import read_compile
from append_method_message_by_dict import append_method_message_by_dict
from append_control_flow_information import append_control_flow_information
from built_corpus import built_corpus_bfs, built_corpus_dfs
from built_vector_dataset import built_vector_dataset
from print_tree import print_tree
from train import train
import datetime
import config
import utils
import os
import shutil

if __name__ == '__main__':
    start = datetime.datetime.now()
    if config.run_mode == "create":
        # 先验证四个重要的文件夹是否存在，不存在则创建。
        utils.dir_exists(config.img_dir_path)
        utils.dir_exists(config.data_sol_source_dir_path)
        utils.dir_exists(config.data_ast_json_dir_path)
        utils.dir_exists(config.data_complete_dir_path)
        utils.dir_exists(config.data_raw_dir_path)
        # 循环sol_source文件夹，获取每一个工程文件夹的名字。
        for project_name in os.listdir(config.data_sol_source_dir_path):
            # sol_source中遍历到的工程文件夹的全路径。
            data_sol_source_project_dir_path = f'{config.data_sol_source_dir_path}/{project_name}'
            data_ast_json_project_dir_path = f'{config.data_ast_json_dir_path}/{project_name}'
            # 删除对应工程文件夹中的注释。
            remove_comments(data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 如果当前工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                os.rmdir(data_sol_source_project_dir_path)
                continue
            # 编译文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
            compile_files(data_sol_source_project_dir_path=data_sol_source_project_dir_path, data_ast_json_project_dir_path=data_ast_json_project_dir_path)
            # 如果当前工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                os.rmdir(data_sol_source_project_dir_path)
                continue
            # 读取工程文件夹对应的AST_JSON中的文件内容。同时要返回节点列表和节点字典。
            project_node_list, project_node_dict = read_compile(data_sol_source_project_dir_path=data_sol_source_project_dir_path, data_ast_json_project_dir_path=data_ast_json_project_dir_path)
            # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
            append_method_message_by_dict(project_node_dict=project_node_dict, data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
            append_control_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
            built_corpus_bfs(project_node_list=project_node_list, data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            built_corpus_dfs(project_node_list=project_node_list, data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 创建数据集
            built_vector_dataset(project_node_list=project_node_list, graph_dataset_dir_path=config.data_raw_dir_path, data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 如果是冻结模式，直接移动文件到already中，代表这个文件下次运行不用操作。
            if config.frozen == "frozen":
                shutil.move(data_sol_source_project_dir_path, config.data_complete_dir_path)
            # 打印树的样子。
            print_tree(project_node_list)
    elif config.run_mode == "train":
        train()
    end = datetime.datetime.now()
    print("开始时间:", start)
    print("结束时间:", end)
    print("一共耗时:", end - start)
