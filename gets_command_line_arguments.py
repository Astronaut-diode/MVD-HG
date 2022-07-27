import argparse
import config


# 获取命令行参数
def gets_command_line_arguments():
    parser = argparse.ArgumentParser(description='manual to this script')
    # create:创建数据集的时候用的
    # train:训练模式
    # valid:预测模式
    # truncated:语言模型受损，需要重新训练。
    parser.add_argument('--run_mode', type=str)
    # create_corpus_txt:仅仅创建语料库文件，当进行训练和预测的时候。
    # generate_all: 生成所有的向量文件
    parser.add_argument('--create_corpus_mode', type=str)
    # 下面更新config配置
    args = parser.parse_args()
    config.run_mode = args.run_mode
    config.create_corpus_mode = args.create_corpus_mode
