import os
import shutil
import math
import random


# 切割目标目录文件夹下面的内容，分到n个目标目录中。按照下面的格式输入会将data/sol_source/下面的文件夹全部分割道*/sol_source/底下去。
def split_dir_file():
    # r"/home/xjj/data/sol_source/"
    source_dir = input("输入需要分割的目录")
    # r"/home/xjj/*/sol_source/"
    target_pattern = input("输入录入的目标目录，使用*代替需要变换的数字,会生成n个该目录，*变为1～n。")
    # 文件夹个数。
    n = input("输入需要分割为多少个子集")
    target_dir = []
    for i in range(int(n)):
        target_dir.append(target_pattern.replace("*", str(i + 1)))
    # 文件的总个数是len(os.listdir(source_dir))
    total = len(os.listdir(source_dir))
    # 计算出如果是完整的应该是多少
    average = math.ceil(total / int(n))
    # 保存每个文件夹里应该保存多少个文件
    counts = []
    # 记录前n - 1个文件夹中保存多少文件的数量和。
    sum = 0
    # 先记录完整的部分有多少个。
    for i in range(int(n) - 1):
        counts.append(average)
        sum += average
    if sum != total:
        counts.append(total - sum)
    # 每个目标文件夹为zip_dict[1],每个文件夹中需要保存多少的文件数量是zip_dict[0]
    for zip_dict in zip(counts, target_dir):
        list = os.listdir(source_dir)
        random.shuffle(list)
        # 重新循环当前的源目录，每一次进来的时候源目录的数量都是会发生变化的，因为下面用的move而不是copy。
        for index, file in enumerate(list):
            # 先判断目标目录是否存在，不存在就先创建。
            if not os.path.exists(zip_dict[1]):
                os.makedirs(zip_dict[1])
            # 如果当前文件夹个数满了，一定要及时退出，转到下一个文件夹中。
            if index == zip_dict[0]:
                break
            else:
                shutil.move(os.path.join(source_dir, file), os.path.join(zip_dict[1], file))


if __name__ == '__main__':
    func = input("请输入你选择的功能:")
    if func == "1":
        split_dir_file()
