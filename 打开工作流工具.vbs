Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
toolPath = fso.BuildPath(scriptDir, "workflow-tool.pyw")

shell.Run "pyw """ & toolPath & """", 0, False
