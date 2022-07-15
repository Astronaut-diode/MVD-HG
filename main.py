# coding=UTF-8
from remove_comments import remove_comments
from compile_files import compile_files
from read_compile import read_compile
from append_method_message_by_dict import append_method_message_by_dict
from append_control_flow_information import append_control_flow_information
from built_corpus import built_corpus_bfs, built_corpus_dfs
from built_vector_dataset import built_vector_dataset
from print_tree import print_tree
from train import train
from gensim.models.word2vec import Word2Vec
from tqdm import tqdm
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
        # 先获取原始标签的json，然后根据json中的内容，可以得到一个列表，其中是没有空隙的，我可以直接获取对应的下标的标签。上面操作的project_name就是对应的下标。
        label_in_memory = utils.get_label()
        # 循环sol_source文件夹，获取每一个工程文件夹的名字。
        for project_name in tqdm(os.listdir(config.data_sol_source_dir_path)):
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
            built_vector_dataset(project_node_list=project_node_list, graph_dataset_dir_path=f'{config.data_raw_dir_path}/{project_name}/', data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 将一个新的节点传进去，然后更新到数据集中。
            utils.update_sol_to_label({f'{project_name}.sol': label_in_memory[int(project_name)][project_name]})
            # 如果是冻结模式，直接移动文件到already中，代表这个文件下次运行不用操作。
            if config.frozen == "frozen":
                shutil.move(data_sol_source_project_dir_path, config.data_complete_dir_path)
            # 打印树的样子。
            print_tree(project_node_list)
        # 如果是create代表上面的循环是为了获取语料，下面训练模型。否则是update，这里不走，但是走上面的built_vector_bfs和dfs的方法。
        if config.create_corpus_mode == "create":
            sentences = []
            # 读取之前保存的语料文件，因为是a b c d这样保存的，所以读出来，然后用空格断句，就能得到一个列表，再append到sentences中就是二维数组，可以直接作为sentences输入到模型中训练。
            with open(config.corpus_txt_path, 'r', encoding="utf-8") as corpus_file:
                for line in corpus_file.readlines():
                    sentences.append(line.split(" "))
            # 因为之前没有文件，所以先进行训练,
            w2v = Word2Vec(sentences=sentences, size=config.encode_dim, workers=16, sg=1, min_count=1)
            # 保存训练以后的模型。
            w2v.save(config.corpus_file_path)
            print("word2Vec模型已经构建完毕.")
    elif config.run_mode == "train":
        train()
    end = datetime.datetime.now()
    print(f"开始时间:{start}")
    print(f"结束时间:{end}")
    print(f"一共耗时:f{end - start}")
