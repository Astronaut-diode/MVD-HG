# MVD-HG

## Introduce

为Smart Contract提取以AST、CFG、DFG为基础的异构图，使用图神经网络进行多粒度的分类，实现行级别以及合约级别的漏洞检测任务。

## Usage

在dataset.zip中已经压缩了28组数据集。分别是7种漏洞类型，每组漏洞类型都分为原始合约级别，增强以后合约级别、原始行级别、增强后行级别。每个文件夹中都存有对应的cmd命令，可用于运行、测试。

## Expermental Results

数据集组成

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/77d0cb79-a74b-42bf-947a-e82b59480f13)

原始合约级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/5ce6a939-0feb-4f85-a037-bf330c9b1bb1)

原始行级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/4e21da8f-4368-4d34-aa2b-27640bc6f987)

使用数据增强以后的合约级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/a8d8f1c5-128d-4cf4-b988-c7c24da8aca9)

使用数据增强以后的行级别漏洞检测结果，'\\'代表不具备该漏洞类型的检测能力。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/705ed97f-84f5-49cc-baad-7b97f8f52577)

不同类型组成异构图的消融实验结果(增强以后的数据集)。

![image](https://github.com/Astronaut-diode/MVD-HG/assets/57606131/26496d3e-9d75-4270-baf4-fa1820b844d0)

## Maintainers

[@Astronaut-diode](https://github.com/Astronaut-diode) 

浙江工业大学 软件工程专业硕士在读

邮箱地址:925791559@qq.com
