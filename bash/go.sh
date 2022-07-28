output1=`nohup python3 main.py --run_mode create --create_corpus_mode create_corpus_txt > /home/xjj/AST-GNN/data/log 2>&1`
if [[ $? -eq 47 ]]; then
	output2=`nohup python3 main.py --run_mode create --create_corpus_mode generate_all > /home/xjj/AST-GNN/data/log 2>&1`
	if [[ $? -eq 47 ]]; then
		output3=`nohup python3 main.py --run_mode train --create_corpus_mode train > /home/xjj/AST-GNN/data/log 2>&1`
	else
		echo "构造训练的原始数据失败"
	fi
else
	echo "构造语料库失败"
fi