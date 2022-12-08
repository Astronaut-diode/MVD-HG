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
from make_timestamp_attack_label import make_timestamp_attack_label
from hash_code import has_equal_hash
from load_model_to_predict import load_model_to_predict
from line_classification.line_classification_train import line_classification_train
from contract_classification.contract_classification_train import contract_classification_train
import datetime
import config
import utils
import os
import shutil
import torch
import sys
import math

if __name__ == '__main__':
    start = datetime.datetime.now()
    if config.run_mode == "create":
        # 先验证四个重要的文件夹是否存在，不存在则创建。
        utils.dir_exists(config.img_dir_path)
        utils.dir_exists(config.data_sol_source_dir_path)
        utils.dir_exists(config.data_ast_json_dir_path)
        utils.dir_exists(config.data_complete_dir_path)
        utils.dir_exists(config.data_raw_dir_path)
        # 保存预测全体内容的文件夹
        utils.dir_exists(config.wait_predict_fold)
        # 判断漏洞文件夹是否存在，不存在则创建
        utils.dir_exists(config.reentry_attack_fold)
        utils.dir_exists(config.timestamp_attack_fold)
        utils.dir_exists(config.arithmetic_attack_fold)
        # 判断问题文件夹是否存在，不存在则创建。
        utils.dir_exists(config.error_file_fold)
        # 判断没有漏洞的文件夹是否存在，不存在则创建。
        utils.dir_exists(config.no_attack_fold)
        # 先创建词向量模型的对象，因为在create_corpus的时候还没有这个文件，肯定是不会加载的。
        word2vec_model = None
        if config.create_corpus_mode == "generate_all":
            # 加载词向量的模型
            word2vec_model = Word2Vec.load(config.corpus_file_path).wv
        # 循环sol_source文件夹，获取每一个工程文件夹的名字。
        for project_name in tqdm(os.listdir(config.data_sol_source_dir_path)):
            # sol_source中遍历到的工程文件夹的全路径。
            data_sol_source_project_dir_path = f'{config.data_sol_source_dir_path}/{project_name}'
            data_ast_json_project_dir_path = f'{config.data_ast_json_dir_path}/{project_name}'
            # 删除对应sol_source下工程文件夹中的注释。
            remove_comments(data_sol_source_project_dir_path=data_sol_source_project_dir_path)
            # 如果已经存在了相同的hash值，那就删除当前的工程文件夹，同时跳过后续处理。
            if has_equal_hash(dir_path=data_sol_source_project_dir_path):
                shutil.rmtree(data_sol_source_project_dir_path)
                utils.error(f"{data_sol_source_project_dir_path}出现重复，已被删除，并跳过后续操作。")
                continue
            # 如果当前sol_source下工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                continue
            try:
                # 编译sol_source下工程文件夹内所有的文件,同时在AST_json中生成对应的文件夹，如果发现编译失败，删除对应的源文件。
                compile_files(data_sol_source_project_dir_path=data_sol_source_project_dir_path, data_ast_json_project_dir_path=data_ast_json_project_dir_path)
            except Exception as e:
                # 编译的时候发现出现了错误，无法进行继续编译，所以先删除掉。
                shutil.rmtree(data_sol_source_project_dir_path)
                utils.error(f"{data_sol_source_project_dir_path}出现问题，已被删除，并跳过后续操作。")
                continue
            # 如果当前sol_source下工程文件夹内部是空的，那就删除文件夹，跳过当前循环。
            if utils.is_blank_now_dir(dir_path=data_sol_source_project_dir_path):
                continue
            # 遍历AST_json中的某一个工程文件夹
            for now_dir, child_dirs, child_files in os.walk(data_ast_json_project_dir_path):
                # 遍历工程项目中的每一个文件
                for ast_json_file_name in child_files:
                    # 读取每个节点代表的源代码的同时，设置所属行数以及所属的文件。
                    project_node_list, project_node_dict = read_compile(now_dir=now_dir, ast_json_file_name=ast_json_file_name)
                    try:
                        # 设置FunctionDefinition还有ModifierDefinition节点中的method_name还有params两个参数，方便后面设置控制流的时候的操作。
                        # 同时对所有函数节点为根的子树，设置所属函数。
                        append_method_message_by_dict(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    except Exception as e:
                        # 发现错误，但是这里的错误并不是致命的，反正文件多，移到错误文件夹中算了。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        utils.error(f"{now_dir}/{ast_json_file_name}出现错误，移入错误文件夹,并跳过后续操作。")
                        continue
                    try:
                        # 传入工程文件夹完全读完以后的节点列表和节点字典，生成对应的控制流边。
                        append_control_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                        # 根据内存中的数据，设定图的数据流。
                        append_data_flow_information(project_node_list=project_node_list, project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                    except Exception as e:
                        # 添加数据流和控制流的时候出错了，删除源文件。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        utils.error(f"{now_dir}/{ast_json_file_name}{e}")
                        continue
                    try:
                        # 判断文件中是否含有漏洞。
                        # 一次性检测多种漏洞，后面自己处理一下文件即可，这样就不用跑三趟了。
                        # 暂时改掉，为了不浪费时间
                        if config.attack_type_name == "all1":
                            reentry_flag = make_reentry_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            timestamp_flag = make_timestamp_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            arithmetic_flag = make_arithmetic_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            # 避免第二次运行的时候覆盖了第一次计算出来的标签。
                            if config.create_corpus_mode != "generate_all":
                                utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [reentry_flag, timestamp_flag, arithmetic_flag])
                        # 暂时改掉，为了不浪费时间
                        if config.attack_type_name == "reentry1":
                            reentry_flag = make_reentry_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            # 避免第二次运行的时候覆盖了第一次计算出来的标签。
                            if config.create_corpus_mode != "generate_all":
                                utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [reentry_flag])
                        # 暂时改掉，为了不浪费时间
                        if config.attack_type_name == "timestamp1":
                            timestamp_flag = make_timestamp_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            # 避免第二次运行的时候覆盖了第一次计算出来的标签。
                            if config.create_corpus_mode != "generate_all":
                                utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [timestamp_flag])
                        # 暂时改掉，为了不浪费时间
                        if config.attack_type_name == "arithmetic1":
                            arithmetic_flag = make_arithmetic_attack_label(project_node_dict=project_node_dict, file_name=f"{now_dir}/{ast_json_file_name}")
                            # 避免第二次运行的时候覆盖了第一次计算出来的标签。
                            if config.create_corpus_mode != "generate_all":
                                utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [arithmetic_flag])
                        # 为了节省时间，不管什么类型，都直接标记为0
                        # if config not in ["all", "reentry", "timestamp", "arithmetic"]:
                            # 避免第二次运行的时候覆盖了第一次计算出来的标签。
                        if config.create_corpus_mode != "generate_all":
                            utils.update_label_file(f"{now_dir}/{ast_json_file_name}", [0])
                    except utils.CustomError as e:
                        # 运行时间过长，是里面的控制流太多了，但是这里的错误并不是致命的，反正文件多，移到错误文件夹中算了。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        utils.error(f"{now_dir}/{ast_json_file_name}{e}")
                        continue
                    # 如果控制流过多，执行上述的函数，可能会出现递归栈溢出的错误，捕获以后继续执行。
                    except RecursionError as e:
                        # 路径爆炸了，导致深度出现问题，删除源文件，并跳过。
                        utils.remove_file(file_path=f"{now_dir}/{ast_json_file_name}")
                        utils.error(f"{now_dir}/{ast_json_file_name}{e}")
                        continue
                    # 为当前这个工程文件夹中所有的文件构建语料库，如果还有下一个文件，到时候再加进去。
                    built_corpus_bfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    built_corpus_dfs(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
                    # 创建数据集
                    built_vector_dataset(project_node_list=project_node_list, file_name=f"{now_dir}/{ast_json_file_name}", word2vec_model=word2vec_model)
                    # 打印树的样子。
                    generate_svg(project_node_list, file_name=f"{now_dir}/{ast_json_file_name}")
            # 如果是冻结模式，直接移动文件到complete文件夹中，代表这个文件下次运行不用操作。这里还是移动文件夹好了，如果移动文件，其中的引用文件被挪走会出事的。
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
                        sentences.append(line.split(config.split_word))
                # 因为之前没有文件，所以先进行训练,
                w2v = Word2Vec(sentences=sentences, size=config.encode_dim, workers=16, sg=1, min_count=1)
                # 保存训练以后的模型。
                w2v.save(config.corpus_file_path)
                # 第一次训练完以后先把complete中的内容都重新移动到sol_source目录当中。这样不就不需要手动重新移动了。
                shutil.rmtree(config.data_sol_source_dir_path)
                os.rename(config.data_complete_dir_path, config.data_sol_source_dir_path)
                utils.success("word2Vec模型已经构建完毕.")
    elif config.run_mode == "truncated":
        sentences = []
        # 读取之前保存的语料文件，因为是a b c d这样保存的，所以读出来，然后用空格断句，就能得到一个列表，再append到sentences中就是二维数组，可以直接作为sentences输入到模型中训练。
        with open(config.corpus_txt_path, 'r', encoding="utf-8") as corpus_file:
            for line in corpus_file.readlines():
                sentences.append(line.split(config.split_word))
        # 因为之前没有文件，所以先进行训练,
        w2v = Word2Vec(sentences=sentences, size=config.encode_dim, workers=16, sg=1, min_count=1)
        # 保存训练以后的模型。
        w2v.save(config.corpus_file_path)
        utils.success("word2Vec模型已经构建完毕.")
    elif config.run_mode == "train":
        # 判断模型文件夹是否存在，不存在则创建。
        utils.dir_exists(config.model_data_dir)
        train()
    # 进行源代码行级别分类的训练
    elif config.run_mode == "line_classification_train":
        res = []
        utils.dir_exists(config.model_data_dir)
        i = 1
        while i <= config.average_num:
            print(f"第{i}趟")
            tmp = line_classification_train()
            flag = False
            for content in tmp:
                if type(content) == datetime.timedelta:
                    continue
                elif type(content) == torch.Tensor:
                    if math.isnan(content.item()):
                        flag = True
                else:
                    if math.isnan(content):
                        flag = True
            if flag:
                print(f"原始结果为:{tmp}")
                print(f"第{i}趟中出现了nan，重新进行计算，不计入最终结果。")
                i -= 1
            else:
                res.append(tmp)
            i += 1
        for i in range(config.average_num):
            print(f"第{i + 1}趟")
            res.append(line_classification_train())
        ans = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for r in res:
            for index, content in enumerate(r):
                if type(content) == datetime.timedelta:
                    ans[index] += (content.total_seconds() / config.average_num)
                elif type(content) == torch.Tensor:
                    ans[index] += (content.item() / config.average_num)
                else:
                    ans[index] += (content / config.average_num)
        with open(f"{config.data_dir_path}/ans.txt", 'w') as write_file:
            for r in res:
                for index, content in enumerate(r):
                    if type(content) == datetime.timedelta:
                        write_file.write(f"{content.total_seconds()} ")
                    elif type(content) == torch.Tensor:
                        write_file.write(f"{content.item()} ")
                    else:
                        write_file.write(f"{content} ")
                write_file.write("\n")
            for index, content in enumerate(ans):
                if type(content) == datetime.timedelta:
                    write_file.write(f"{content.total_seconds()} ")
                elif type(content) == torch.Tensor:
                    write_file.write(f"{content.item()} ")
                else:
                    write_file.write(f"{content} ")
            write_file.write("\n")
    elif config.run_mode == "contract_classification_train":
        res = []
        utils.dir_exists(config.model_data_dir)
        i = 1
        while i <= config.average_num:
            print(f"第{i}趟")
            tmp = contract_classification_train()
            flag = False
            for content in tmp:
                if type(content) == datetime.timedelta:
                    continue
                elif type(content) == torch.Tensor:
                    if math.isnan(content.item()):
                        flag = True
                else:
                    if math.isnan(content):
                        flag = True
            if flag:
                print(f"原始结果为:{tmp}")
                print(f"第{i}趟中出现了nan，重新进行计算，不计入最终结果。")
                i -= 1
            else:
                res.append(tmp)
            i += 1
        ans = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for r in res:
            for index, content in enumerate(r):
                if type(content) == datetime.timedelta:
                    ans[index] += (content.total_seconds() / config.average_num)
                elif type(content) == torch.Tensor:
                    ans[index] += (content.item() / config.average_num)
                else:
                    ans[index] += (content / config.average_num)
        with open(f"{config.data_dir_path}/ans.txt", 'w') as write_file:
            for r in res:
                for index, content in enumerate(r):
                    if type(content) == datetime.timedelta:
                        write_file.write(f"{content.total_seconds()} ")
                    elif type(content) == torch.Tensor:
                        write_file.write(f"{content.item()} ")
                    else:
                        write_file.write(f"{content} ")
                write_file.write("\n")
            for index, content in enumerate(ans):
                if type(content) == datetime.timedelta:
                    write_file.write(f"{content.total_seconds()} ")
                elif type(content) == torch.Tensor:
                    write_file.write(f"{content.item()} ")
                else:
                    write_file.write(f"{content} ")
    elif config.run_mode == "predict":
        # 保存模型的文件夹
        utils.dir_exists(config.model_data_dir)
        # 保存预测全体内容的文件夹
        utils.dir_exists(config.wait_predict_fold)
        # 保存预测原始智能合约的文件夹
        utils.dir_exists(config.wait_predict_sol_source_fold)
        # 保存智能合约编译后json文件的文件夹
        utils.dir_exists(config.wait_predict_ast_json_fold)
        # 保存智能合约转化为图结构数据的文件夹
        utils.dir_exists(config.wait_predict_data_raw_dir_path)
        load_model_to_predict()
    end = datetime.datetime.now()
    utils.tip(f"开始时间:{start}")
    utils.tip(f"结束时间:{end}")
    utils.tip(f"一共耗时:{end - start}")
    utils.tip("以下是使用的参数")
    utils.tip(f"run_mode:{config.run_mode}")
    utils.tip(f"create_corpus_mode:{config.create_corpus_mode}")
    sys.exit(47)
