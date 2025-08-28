@echo off
setlocal EnableDelayedExpansion

REM SlackToJournal Environment Setup Script
REM Auto-install and configure environment

echo.
echo ============================================
echo SlackToJournal Environment Setup
echo ============================================
echo.

REM Check if uv is installed
echo [1/6] Checking if uv is installed...
where uv >nul 2>&1
if %ERRORLEVEL% == 0 (
    for /f "delims=" %%i in ('uv --version 2^>nul') do set UV_VERSION=%%i
    echo [SUCCESS] uv is already installed: !UV_VERSION!
    goto :uv_ready
)

echo [INFO] uv not found, installing...
echo [INFO] This may take a few minutes, please wait...
echo.

REM Try PowerShell installation with timeout
echo [INFO] Attempting installation with PowerShell Core...
timeout /t 1 >nul 2>&1
pwsh -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" 2>nul
if %ERRORLEVEL% == 0 (
    echo [SUCCESS] uv installation successful with PowerShell Core
    goto :verify_installation
)

echo [INFO] Trying Windows PowerShell...
timeout /t 1 >nul 2>&1
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" 2>nul
if %ERRORLEVEL% == 0 (
    echo [SUCCESS] uv installation successful with Windows PowerShell
    goto :verify_installation
)

echo [ERROR] uv installation failed
echo.
echo Please install uv manually:
echo 1. Visit: https://github.com/astral-sh/uv/releases
echo 2. Download and run the installer
echo 3. Restart this script
echo.
pause
exit /b 1

:verify_installation
echo [INFO] Verifying uv installation...
timeout /t 3 >nul 2>&1

REM Add uv to PATH
set "PATH=%USERPROFILE%\.cargo\bin;%USERPROFILE%\.local\bin;%PATH%"

where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    if exist "%USERPROFILE%\.cargo\bin\uv.exe" (
        set "UV_PATH=%USERPROFILE%\.cargo\bin\uv.exe"
        echo [SUCCESS] Found uv at: !UV_PATH!
    ) else if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV_PATH=%USERPROFILE%\.local\bin\uv.exe"
        echo [SUCCESS] Found uv at: !UV_PATH!
    ) else (
        echo [ERROR] Could not locate uv executable
        pause
        exit /b 1
    )
) else (
    echo [SUCCESS] uv verified in PATH
)

:uv_ready
echo.

REM Determine uv command
if defined UV_PATH (
    set "UV_CMD="%UV_PATH%""
) else (
    set "UV_CMD=uv"
)

REM Check Python
echo [2/6] Checking Python version...
%UV_CMD% python list >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [INFO] Installing Python...
    %UV_CMD% python install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python installation failed
        pause
        exit /b 1
    )
    echo [SUCCESS] Python installed
) else (
    REM Check for Python 3.11+
    for /f "delims=" %%i in ('%UV_CMD% python list 2^>nul ^| findstr "cpython-3.1[1-9]\|cpython-3.[2-9]" 2^>nul') do (
        for /f "tokens=1" %%j in ("%%i") do set PYTHON_VERSION=%%j
        goto :python_found
    )
    
    echo [INFO] Installing Python 3.11+...
    %UV_CMD% python install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Python installation failed
        pause
        exit /b 1
    )
    echo [SUCCESS] Python installed
    goto :python_done
)

:python_found
echo [SUCCESS] Found Python: !PYTHON_VERSION!

:python_done
echo.

REM Check project files
echo [3/6] Checking project configuration...
if not exist ".env.example" (
    echo [ERROR] .env.example not found
    echo [ERROR] Please run this script from the SlackToJournal directory
    echo [INFO] Current directory: %CD%
    pause
    exit /b 1
)

REM Sync dependencies
echo [4/6] Installing project dependencies...
echo [INFO] This may take a few minutes...
%UV_CMD% sync --native-tls --link-mode=copy
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Dependencies installation failed
    echo [ERROR] Check your internet connection and try again
    pause
    exit /b 1
)
echo [SUCCESS] Dependencies installed

echo.

REM Setup .env file
echo [5/6] Configuring environment...
if not exist ".env" (
    REM Use PowerShell to copy with correct encoding
    powershell -Command "Get-Content '.env.example' -Encoding UTF8 | Set-Content '.env' -Encoding UTF8"
    echo [SUCCESS] .env file created with correct encoding
) else (
    echo [SUCCESS] .env file exists
)

REM Check if API keys need configuration
findstr /C:"your-bot-token-here" ".env" >nul 2>&1
set BOT_DEFAULT=%ERRORLEVEL%
findstr /C:"your-gemini-api-key-here" ".env" >nul 2>&1
set GEMINI_DEFAULT=%ERRORLEVEL%

if %BOT_DEFAULT% == 0 if %GEMINI_DEFAULT% == 0 (
    echo [INFO] API keys need configuration
    goto :configure_keys
) else (
    echo [SUCCESS] API keys already configured
    goto :completion
)

:configure_keys
echo.
echo [6/6] Configuring API keys...
echo.
echo Please enter your API keys:
echo.

:get_slack_token
set /p SLACK_BOT_TOKEN="SLACK_BOT_TOKEN (xoxb-...): "
if "!SLACK_BOT_TOKEN!"=="" (
    echo [ERROR] Token cannot be empty
    goto :get_slack_token
)

set /p SLACK_USER_TOKEN="SLACK_USER_TOKEN (optional, xoxp-... or press Enter): "

:get_gemini_key
set /p GEMINI_API_KEY="GEMINI_API_KEY: "
if "!GEMINI_API_KEY!"=="" (
    echo [ERROR] API key cannot be empty
    goto :get_gemini_key
)

echo.
echo [INFO] Updating configuration...
powershell -Command "(Get-Content '.env' -Encoding UTF8) -replace 'SLACK_BOT_TOKEN=.*', 'SLACK_BOT_TOKEN=!SLACK_BOT_TOKEN!' | Set-Content '.env' -Encoding UTF8" >nul 2>&1
if not "!SLACK_USER_TOKEN!"=="" (
    powershell -Command "(Get-Content '.env' -Encoding UTF8) -replace 'SLACK_USER_TOKEN=.*', 'SLACK_USER_TOKEN=!SLACK_USER_TOKEN!' | Set-Content '.env' -Encoding UTF8" >nul 2>&1
)
powershell -Command "(Get-Content '.env') -replace 'GEMINI_API_KEY=.*', 'GEMINI_API_KEY=!GEMINI_API_KEY!' | Set-Content '.env' -Encoding UTF8" >nul 2>&1

echo [SUCCESS] Configuration updated

:completion
echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Usage:
echo   Weekly report: uv run -m src.main weekly -n "Your Name"
echo   Daily report:  uv run -m src.main daily -n "Your Name"
echo.
echo Next steps:
echo 1. Add your Slack bot to relevant channels
echo 2. Edit .env file if needed
echo 3. Run your first report!
echo.
pause