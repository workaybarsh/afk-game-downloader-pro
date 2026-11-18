' AFK Game Downloader Pro - silent launcher (no console window).
' Double-click this file to start the app.

Option Explicit

Dim shell, fso, folder, cmd, ok

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder

ok = False

' 1) Try the py launcher's windowless executable
On Error Resume Next
cmd = "pyw.exe -3 """ & folder & "\main.pyw"""
shell.Run cmd, 0, False
If Err.Number = 0 Then ok = True
Err.Clear

' 2) Fall back to pythonw from PATH
If Not ok Then
    cmd = "pythonw.exe """ & folder & "\main.pyw"""
    shell.Run cmd, 0, False
    If Err.Number = 0 Then ok = True
    Err.Clear
End If

' 3) Last resort: run with a console so the user can see the error
If Not ok Then
    MsgBox "Python was not found. Install Python 3.10+ or run build_exe.bat to create a standalone .exe.", 16, "AFK Game Downloader Pro"
End If

On Error GoTo 0
