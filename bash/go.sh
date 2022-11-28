output1=`nohup python3 main.py --run_mode create --create_corpus_mode create_corpus_txt --data_dir_name test --attack_type_name reentry 2>&1`
if [[ $? -eq 47 ]]; then
	output2=`nohup python3 main.py --run_mode create --create_corpus_mode generate_all --data_dir_name test --attack_type_name reentry 2>&1`
	if [[ $? -eq 47 ]]; then
		output3=`nohup python3 main.py --run_mode train --create_corpus_mode generate_all --data_dir_name test --attack_type_name reentry 2>&1`
		if [[ $? -eq 47 ]]; then
		    output4=`nohup python3 main.py --run_mode train --create_corpus_mode generate_all --data_dir_name test --attack_type_name reentry 2>&1`
		else
		    echo "训练失败"
	else
		echo "构造训练的原始数据失败"
	fi
else
	echo "构造语料库失败"
fi