# coding=UTF-8
from remove_comments import remove_comments
from compile_files import compile_files
from read_compile import read_compile
from append_method_message_by_dict import append_method_message_by_dict
from append_control_flow_information import append_control_flow_information
from built_corpus import built_corpus_bfs, built_corpus_dfs
from built_vector_dataset import built_vector_dataset
from print_tree import generate_svg
from train import train
from gensim.models.word2vec import Word2Vec
from append_data_flow_information import append_data_flow_information
from make_reentry_attack_label import make_reentry_attack_label
from make_arithmetic_attack_label import make_arithmetic_attack_label
from classification_of_documents import classification_of_documents
from tqdm import tqdm
from gets_command_line_arguments import gets_command_line_arguments
import datetime
import config
import utils
import os
import shutil
import sys

if __name__ == '__main__':
    # 先获取命令行参数，更新config配置。
    gets_command_line_arguments()
    start = datetime.datetime.now()
    if config.run_mode == "create":
        # 先验证四个重要的文件夹是否存在，不存在则创建。
        utils.dir_exists(config.img_dir_path)
        utils.dir_exists(config.data_sol_source_dir_path)
        utils.dir_exists(config.data_ast_json_dir_path)
        utils.dir_exists(config.data_complete_dir_path)
        utils.dir_exists(config.data_raw_dir_path)
        # 判断漏洞文件夹是否存在，不存在则创建
        utils.dir_exists(config.reentry_attack_fold)
        utils.dir_exists(config.timestamp_attack_fold)
        utils.dir_exists(config.arithmetic_attack_fold)
        utils.dir_exists(config.dangerous_delegate_call_attack_fold)
        # 判断问题文件夹是否存在，不存在则创建。
        utils.dir_exists(config.error_file_fold)
        # 循环sol_source文件夹，获取每一个工程文件夹的名字。
        for project_name in tqdm(os.listdir(config.data_sol_source_dir_path)):
            # sol_source中遍历到的工程文件夹的全路径。
            data_sol_source_project_dir_path = f'{config.data_sol_source_dir_path}/{project_name}'
            data_ast_json_project_dir_path = f'{config.data_ast_json_dir_path}/{project_name}'
            # 删除对应sol_source下工程文件夹中的注释。
            remove_comments(data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 如果当前sol_source下工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                continue
            # 编译sol_source下工程文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
            compile_files(data_sol_source_project_dir_path=data_sol_source_project_dir_path, data_ast_json_project_dir_path=data_ast_json_project_dir_path)
            # 如果当前sol_source下工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                continue
            # 遍历AST_json中的某一个工程文件夹
            for now_dir, child_dirs, child_files in os.walk(data_ast_json_project_dir_path):
                # 遍历工程项目中的每一个文件
                for ast_json_file_name in child_files:
                    project_node_list, project_node_dict = read_compile(now_dir=now_dir, ast_json_file_name=ast_json_file_name)
                    try:
                        # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
                        append_method_message_by_dict(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    except Exception as e:
                        # 发现错误，但是这里的错误并不是致命的，反正文件多，移到错误文件夹中算了。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        print(f"{now_dir}/{ast_json_file_name}出现错误，移入错误文件夹,并跳过后续操作。")
                        continue
                    # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
                    append_control_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    try:
                        # 根据内存中的数据，设定图的数据流。
                        append_data_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                        # 判断文件中是否含有漏洞。
                        reentry_flag = make_reentry_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                        arithmetic_flag = make_arithmetic_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                        utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [reentry_flag, 0, arithmetic_flag, 0])
                    except utils.CustomError as e:
                        # 运行时间过长，是里面的控制流太多了，但是这里的错误并不是致命的，反正文件多，移到错误文件夹中算了。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        print(f"{now_dir}/{ast_json_file_name}{e}")
                        continue
                    # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
                    built_corpus_bfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    built_corpus_dfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 创建数据集
                    built_vector_dataset(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 打印树的样子。
                    generate_svg(project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
            # 如果是冻结模式，直接移动文件到already中，代表这个文件下次运行不用操作。这里还是移动文件夹好了，如果移动文件，其中的引用文件被挪走会出事的。
            # 同时还要判断文件夹的是否存在的特性，因为上面的循环可能会删除文件。
            if config.frozen == "frozen" and os.path.exists(data_sol_source_project_dir_path):
                shutil.move(data_sol_source_project_dir_path, config.data_complete_dir_path)
        # 如果是create代表上面的循环是为了获取语料，下面训练模型。否则是update，这里不走，但是走上面的built_vector_bfs和dfs的方法。
        if config.create_corpus_mode == "create_corpus_txt":
            # 需要标签文件和语言库文件都在才能处理。
            if os.path.exists(config.idx_to_label_file) and os.path.exists(config.corpus_txt_path):
                # 同时，处理将这些漏洞文件处理一下，保存到不同文件夹中，方便下一次使用。
                classification_of_documents()
                sentences = []
                # 读取之前保存的语料文件，因为是a b c d这样保存的，所以读出来，然后用空格断句，就能得到一个列表，再append到sentences中就是二维数组，可以直接作为sentences输入到模型中训练。
                with open(config.corpus_txt_path, 'r', encoding="utf-8") as corpus_file:
                    for line in corpus_file.readlines():
                        sentences.append(line.split(" "))
                # 因为之前没有文件，所以先进行训练,
                w2v = Word2Vec(sentences=sentences, size=config.encode_dim, workers=16, sg=1, min_count=1)
                # 保存训练以后的模型。
                w2v.save(config.corpus_file_path)
                # 第一次训练完以后先把complete中的内容都重新移动到sol_source目录当中。这样不就不需要手动重新移动了。
                shutil.rmtree(config.data_sol_source_dir_path)
                os.rename(config.data_complete_dir_path, config.data_sol_source_dir_path)
                print("word2Vec模型已经构建完毕.")
    elif config.run_mode == "truncated":
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
    print(f"一共耗时:{end - start}")
    print("以下是使用的参数")
    print(f"run_mode:{config.run_mode}")
    print(f"create_corpus_mode:{config.create_corpus_mode}")
    sys.exit(47)
