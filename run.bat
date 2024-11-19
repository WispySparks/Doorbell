@ECHO OFF

:start
.venv\Scripts\python.exe test\app_test.py
if %ERRORLEVEL% equ 7880 goto start
    