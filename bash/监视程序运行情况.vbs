Dim WshShell 
Set WshShell=WScript.CreateObject("WScript.Shell") 
WshShell.Run "cmd.exe"
WScript.Sleep 1500 
WshShell.SendKeys "ssh xjj@10.12.49.193"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 1500 
WshShell.SendKeys "nideshengri!"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 2000 
WshShell.SendKeys "source .bashrc"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "conda activate remote_virtue_env"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "cd /home/xjj/AST-GNN/data"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "tail -f log"
WshShell.SendKeys "{ENTER}"
