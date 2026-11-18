@echo off
rem Console launcher - useful when something goes wrong and you need to see the output.
cd /d "%~dp0"
python main.pyw
if errorlevel 1 pause
