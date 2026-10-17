@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PY12=%LOCALAPPDATA%\PyBuild\Python312\python.exe"
if exist "%PY12%" (
    "%PY12%" ble_serial_assistant.py
) else (
    python ble_serial_assistant.py
)
if errorlevel 1 pause
