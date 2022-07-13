from dataset import ASTGNNDataset
import os

parent_path = os.getcwd()
data_path = f'{parent_path}/data/'


def train():
    dataset = ASTGNNDataset(data_path, "AST")
