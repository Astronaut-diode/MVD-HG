import argparse
import config


# 获取命令行参数
def gets_command_line_arguments():
    parser = argparse.ArgumentParser(description='参数表')
    # create:创建数据集的时候用的
    # train:训练模式
    # valid:预测模式
    # truncated:语言模型受损，需要重新训练。
    parser.add_argument('--run_mode', type=str,
                        help="运行模式:\n"
                             "1.create:创建数据集的时候用的。\n"
                             "2.train:训练模式。\n"
                             "3.valid:预测模式。\n"
                             "4.truncated:语言模型受损，需要重新训练。\n")
    # create_corpus_txt:仅仅创建语料库文件。
    # generate_all: 生成所有的向量文件。
    parser.add_argument('--create_corpus_mode', type=str,
                        help="创建文件的模式:\n"
                             "1.create_corpus_txt:仅仅创建语料库文件。\n"
                             "2.generate_all: 生成所有的向量文件。\n")
    # 下面更新config配置
    args = parser.parse_args()
    config.run_mode = args.run_mode
    config.create_corpus_mode = args.create_corpus_mode
