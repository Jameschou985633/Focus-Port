@echo off
cd /d "%~dp0focusport-frontend"
set "PATH=C:\Program Files\Lenovo\AIAgent\mcp\node-v22.16.0-win-x64;%PATH%"
"C:\Program Files\Lenovo\AIAgent\mcp\node-v22.16.0-win-x64\npm.cmd" run dev -- --host 127.0.0.1 --port 5174
