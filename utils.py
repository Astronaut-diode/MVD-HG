import os


# 判断文件夹是否已经存在，如果不存在就创建文件夹
def dir_exists(dir_path):
    if not os.path.exists(dir_path):
        os.mkdir(dir_path)


# 判断当前文件夹内容是不是空的,是空的就返回True。
def is_blank_now_dir(dir_path):
    print(dir_path, "由于内容已经为空，所以被删除了。")
    return len(os.listdir(dir_path)) == 0
