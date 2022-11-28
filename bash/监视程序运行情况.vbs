Dim WshShell 
Set WshShell=WScript.CreateObject("WScript.Shell") 
WshShell.Run "cmd.exe"
WScript.Sleep 1500 
WshShell.SendKeys "ssh astronaut@10.12.49.193"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 1500 
WshShell.SendKeys "Wodeshengri47!"
WshShell.SendKeys "{ENTER}"
WScript.Sleep 2000 
WshShell.SendKeys "source .bashrc"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "conda activate lunikhod"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "cd /data/space_station/AST-GNN/test"
WshShell.SendKeys "{ENTER}"
WshShell.SendKeys "tail -f log"
WshShell.SendKeys "{ENTER}"
