@echo off
setlocal

cd /d "%~dp0"

if "%~1"=="" goto gui
goto cli

:gui
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw gui.py
    exit /b 0
)

where pyw >nul 2>nul
if %errorlevel%==0 (
    start "" pyw -3 gui.py
    exit /b 0
)

echo Python GUI launcher not found. Falling back to console mode.
echo.
call :run_python gui.py
set "exit_code=%errorlevel%"
echo.
pause
exit /b %exit_code%

:cli
call :run_python solver.py %*
set "exit_code=%errorlevel%"
echo.
pause
exit /b %exit_code%

:run_python
python --version >nul 2>nul
if %errorlevel%==0 (
    python %*
    exit /b %errorlevel%
)

py -3 --version >nul 2>nul
if %errorlevel%==0 (
    py -3 %*
    exit /b %errorlevel%
)

echo Python was not found. Install Python 3.11+ and try again.
exit /b 1
