@echo off
chcp 65001 >nul
cd /d %~dp0
set PYTHONPATH=%~dp0src;%PYTHONPATH%
where py >nul 2>nul && (py -m pj_manager.app) || (python -m pj_manager.app)
if errorlevel 1 pause
