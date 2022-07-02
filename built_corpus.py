import os
from queue import Queue, LifoQueue
import re
import config
from gensim.models.word2vec import Word2Vec


# 通过广度遍历的方式构建语料库，其中如果遇见某些节点带有name，literal，value这几种的attribute属性，可以直接取出来一起作为语料。
def built_corpus_bfs(project_node_list):
    # 待会使用Word2Vec的分词列表
    sentences = []
    # 先找到其中的Source节点
    for node in project_node_list:
        # 如果找到了，那就以这个节点为根节点，开始进行深度遍历。
        if node.node_type == "SourceUnit":
            # 广度遍历的队列
            bfs_queue = Queue()
            # 先将根节点插入作为我们出发点
            bfs_queue.put(node)
            # 只要内容不是空，就需要一直进行循环。
            while not bfs_queue.empty():
                # 弹出队列头的节点
                parent = bfs_queue.get()
                # 先将这个节点的节点类型添加到sentences中，实现待会的分词，可以保证每个工程项目都只有一个列表。
                sentences.append(parent.node_type)
                # 判断这个节点是否含有string字符串或者数字或者是方法名，如果有，需要一起添加进去，而且要注意大小驼峰的分割。
                tmp = have_attribute(parent)
                # 如果有返回值，那就所说明确实是含有字符串或者数字或者方法名的
                if tmp:
                    # 如果弹出的内容是str或者int类型，才会选择将他们添加到词库当中去。
                    if isinstance(tmp[0], str) or isinstance(tmp[0], int):
                        # 如果是方法名，那是需要进行大小驼峰的转化的，这样子可以缩减语料库当中单词的数量。
                        for s in hump2sub(tmp[0]):
                            # 将拆分以后的结果一个个的添加到语料库中。
                            sentences.append(s)
                # 如果有子节点，把子节点一个个添加进去
                for child in parent.childes:
                    bfs_queue.put(child)
    # 将这个语料库，添加到我们的pkl文件中去
    if os.path.exists(config.corpus_file_path):
        # 加载之前已经保存好的文件。
        w2v = Word2Vec.load(config.corpus_file_path)
        # 为新的sentence创建内容。
        update_sentences = [sentences]
        # 将这个内容添加到词表中。
        w2v.build_vocab(update_sentences, update=True)
        # 开始训练内容。
        w2v.train(update_sentences, total_examples=w2v.corpus_count, epochs=10)
        # 保存训练以后的模型。
        w2v.save(config.corpus_file_path)
    else:
        # 因为之前没有文件，所以先进行训练。
        w2v = Word2Vec(sentences=[sentences], size=config.encode_dim, workers=16, sg=1, min_count=1)
        # 保存训练以后的模型。
        w2v.save(config.corpus_file_path)


# 改用深度遍历的方式构建语料库，两种方式一起，综合一下。
def built_corpus_dfs(project_node_list):
    # 待会使用Word2Vec的分词列表
    sentences = []
    # 先找到其中的Source节点
    for node in project_node_list:
        # 如果找到了，那就以这个节点为根节点，开始进行深度遍历。
        if node.node_type == "SourceUnit":
            # 广度遍历的队列
            dfs_stack = LifoQueue()
            # 先将根节点插入作为我们出发点
            dfs_stack.put(node)
            # 只要内容不是空，就需要一直进行循环。
            while not dfs_stack.empty():
                # 弹出队列头的节点
                parent = dfs_stack.get()
                # 先将这个节点的节点类型添加到sentences中，实现待会的分词，可以保证每个工程项目都只有一个列表。
                sentences.append(parent.node_type)
                # 判断这个节点是否含有string字符串或者数字或者是方法名，如果有，需要一起添加进去，而且要注意大小驼峰的分割。
                tmp = have_attribute(parent)
                # 如果有返回值，那就所说明确实是含有字符串或者数字或者方法名的
                if tmp:
                    # 如果弹出的内容是str或者int类型，才会选择将他们添加到词库当中去。
                    if isinstance(tmp[0], str) or isinstance(tmp[0], int):
                        # 如果是方法名，那是需要进行大小驼峰的转化的，这样子可以缩减语料库当中单词的数量。
                        for s in hump2sub(tmp[0]):
                            # 将拆分以后的结果一个个的添加到语料库中。
                            sentences.append(s)
                # 如果有子节点，把子节点一个个添加进去
                for child in parent.childes:
                    dfs_stack.put(child)
    # 将这个语料库，添加到我们的pkl文件中去
    if os.path.exists(config.corpus_file_path):
        # 加载之前已经保存好的文件。
        w2v = Word2Vec.load(config.corpus_file_path)
        # 为新的sentence创建内容。
        update_sentences = [sentences]
        # 将这个内容添加到词表中。
        w2v.build_vocab(update_sentences, update=True)
        # 开始训练内容。
        w2v.train(update_sentences, total_examples=w2v.corpus_count, epochs=10)
        # 保存训练以后的模型。
        w2v.save(config.corpus_file_path)
    else:
        # 因为之前没有文件，所以先进行训练。
        w2v = Word2Vec(sentences=[sentences], size=config.encode_dim, workers=16, sg=1, min_count=1)
        # 保存训练以后的模型。
        w2v.save(config.corpus_file_path)


# 判断这个节点是否包含了name，Literal或者value
def have_attribute(node):
    # 如果含有value的信息
    if "value" in node.attribute.keys():
        return node.attribute["value"]
    # 如果含有名字
    if "name" in node.attribute.keys():
        return node.attribute["name"]
    return None


# 拆分原始的大小驼峰信息
def hump2sub(hump_str):
    p = re.compile(r'([a-z]|\d)([A-Z])')
    sub = re.sub(p, r'\1_\2', hump_str).lower()
    q = re.compile(r'([a-z][a-z])([0-9])')
    new_sub = re.sub(q, r'\1_\2', sub)
    seq = re.split('_', new_sub)
    return seq
