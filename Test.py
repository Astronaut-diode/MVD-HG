import argparse
import os
import shutil
import subprocess
import json

# 改变当前工作目录到 /var
os.chdir("/root/MVD-HG")
# 默认会先加载config配置文件夹，然后设定好程序运行的配置。
parser = argparse.ArgumentParser(description='参数表')
# create:创建数据集的时候用的
# train:训练模式
# predict:预测模式,后面这里可能要开两个预测的分支。
# truncated:语言模型受损，需要重新训练。
parser.add_argument('--source_dir', type=str,
                    help="原始目录:\n")
parser.add_argument('--dest_dir', type=str,
                    help="目标目录:\n")
parser.add_argument('--filename', type=str,
                    help="文件名字:\n")
parser.add_argument('--attack_type', type=str,
                    help="漏洞类型:\n")
# 下面更新config配置
args = parser.parse_args()
source_dir = args.source_dir
dest_dir = args.dest_dir
filename = args.filename
attack_type = args.attack_type

source_file = source_dir + "/" + filename
# 确保目标文件夹存在，如果不存在则创建
os.makedirs(dest_dir + "/sol_source/" + str(source_dir).split("/")[-1], exist_ok=True)
# 拷贝文件到目标文件夹
shutil.copy(source_file, dest_dir + "/sol_source/" + str(source_dir).split("/")[-1])

cmd = f"/root/anaconda3/envs/lunikhod/bin/python3 /root/MVD-HG/main.py --run_mode predict_contract --data_dir_name {str(dest_dir).split('/')[-2]} --attack_type_name {attack_type} --coefficient 0.1 --target_dir {source_dir.split('/')[-1]} --target_file {filename}"
print(cmd)
# 创建一个子进程并立即返回
process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# 获取命令的标准输出和标准错误输出
stdout, stderr = process.communicate()
# 输出命令执行结果
print("Command Output:", stdout.decode())
print("Command Output:", stderr.decode())
# 输出命令执行结果
file = open(dest_dir + "/res_contract.json", 'r')
content = json.load(file)
file.close()

# if content[0]['label'] != 0:  # 那就代表有事发生,在原始的日志文件中加入存在这种漏洞的标记。
# with open(source_file.replace(".sol", ".log"), 'a') as log:
#     # log.write(content[0]['attack_type'] + " ")
#     if log
log_json = {}
if os.path.exists(source_file.replace(".sol", ".log")):
    file = open(source_file.replace(".sol", ".log"), 'r')
    log_json = json.load(file)
    file.close()
for c in content:
    if os.path.basename(c['name']) == filename:
        log_json[c['attack_type']] = c['label']


# 将content保存到path上，以json的格式。
def save_json(content, path):
    json_file = open(path, 'w')
    json.dump(content, json_file)
    json_file.close()


save_json(log_json, source_file.replace(".sol", ".log"))
print(source_file.replace(".sol", ".log"))

with open(source_file, 'r') as tmp:
    # 接下来准备将raw文件夹中的对应的json文件移动到java项目中去。
    raw_dir = f"{dest_dir}/raw/{str(source_dir).split('/')[-1]}"
    shutil.copy(raw_dir + '/' + filename.replace(".sol", "_node.json"), source_dir)
    shutil.copy(raw_dir + '/' + filename.replace(".sol", "_ast_edge.json"), source_dir)
    shutil.copy(raw_dir + '/' + filename.replace(".sol", "_cfg_edge.json"), source_dir)
    shutil.copy(raw_dir + '/' + filename.replace(".sol", "_dfg_edge.json"), source_dir)

# def delete_files_in_folder(folder_path):
#     # 遍历文件夹中的所有文件
#     for file_name in os.listdir(folder_path):
#         # 构建文件的完整路径
#         file_path = os.path.join(folder_path, file_name)
#         # 如果是文件夹，则递归调用删除文件夹的函数
#         if os.path.isdir(file_path):
#             shutil.rmtree(file_path)
#         # 如果是文件，则直接删除
#         else:
#             os.remove(file_path)
#
#
# delete_files_in_folder(dest_dir)  # 清楚所有的痕迹，准备下次继续。
