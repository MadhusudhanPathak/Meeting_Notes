@echo off
color 0A
setlocal enabledelayedexpansion

echo Checking if Python is installed...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Installing Python using winget...

    echo Checking if winget is installed...
    winget --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo Error: Winget is not installed. Please install winget first.
        echo Visit https://learn.microsoft.com/en-us/windows/package-manager/winget/
        pause
        exit /b 1
    )

    echo Installing Python using winget...
    winget install -e --id Python.Python.3
    if !errorlevel! neq 0 (
        echo Error: Failed to install Python using winget.
        pause
        exit /b 1
    )

    echo Python installed successfully.
) else (
    echo Python is already installed.
)

echo Checking if pip is available...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Pip is not available. Installing pip...
    python -m ensurepip --upgrade
    if !errorlevel! neq 0 (
        echo Error: Failed to install pip.
        pause
        exit /b 1
    )
    echo Pip installed successfully.
) else (
    echo Pip is already available.
)

echo Checking if all required packages are installed...
python -c "import sys; import pkg_resources; pkg_resources.require(open('requirements.txt', 'r'))" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages from requirements.txt...
    python -m pip install -r requirements.txt
    if !errorlevel! neq 0 (
        echo Error: Failed to install required packages.
        pause
        exit /b 1
    )
    echo Required packages installed successfully.
) else (
    echo All required packages are already installed.
)

echo Running main.py...
python main.py
if %errorlevel% neq 0 (
    echo Error occurred while running main.py
    pause
    exit /b 1
)

echo Finished running main.py
echo Hope it worked out for you..!!

REM Wait 5 seconds before exit
echo Closing in 5 seconds...
timeout /t 5 /nobreak >nul
endlocal
exit /b 0