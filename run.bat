@echo off
chcp 65001 >nul
cd /d %~dp0
where py >nul 2>nul && (py pjman.py) || (python pjman.py)
if errorlevel 1 pause
