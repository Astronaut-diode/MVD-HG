from generate_ast import generate_ast
from read_ast import read_ast

if __name__ == '__main__':
    # 先利用solc的编译器，直接将源代码转化为抽象语法树的AST文件
    generate_ast()
    # 读取抽象语法树文件，并在其中根据json文件，生成图结构数据。
    read_ast()
