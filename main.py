from generate_ast import generate_ast
from read_ast import read_ast
from remove_annotation import remove_annotation
import os

if __name__ == '__main__':
    # 在运行之前先删除之前轮次运行出来的结果
    for project_name in os.listdir("/home/xjj/AST-GNN/data/AST_json/"):
        os.rmdir("/home/xjj/AST-GNN/data/AST_json/" + project_name)
    # 删除源代码中的注释
    remove_annotation()
    # 先利用solc的编译器，直接将源代码转化为抽象语法树的AST文件
    generate_ast()
    # 读取抽象语法树文件，并在其中根据json文件，生成图结构数据。
    read_ast()
