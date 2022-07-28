Dim WshShell 
Set WshShell=WScript.CreateObject("WScript.Shell") 
WshShell.Run "cmd.exe"
WScript.Sleep 1500 
WshShell.SendKeys "ssh -L 6008:127.0.0.1:6008 xjj@10.12.49.193"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 1500 
WshShell.SendKeys "nideshengri!"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 2000 
WshShell.SendKeys "source ~/.bashrc"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "conda activate remote_virtue_env"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "cd /home/xjj/AST-GNN/data/"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "tensorboard --logdir ./tensorboard_logs --port 6008"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 10000 
Set s = CreateObject("WScript.Shell")
s.Run"""C:\Program Files\Google\Chrome\Application\chrome.exe""" & "http://localhost:6008/"