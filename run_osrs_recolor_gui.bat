@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 osrs_recolor_gui.py
) else (
    python osrs_recolor_gui.py
)
endlocal
