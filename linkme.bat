@echo off
chcp 65001 >nul
set CWD=%~dp0
if "%CWD:~-1%"=="\" set CWD=%CWD:~0,-1%

set PROJECT_NAME=專屬計畫書 🌸
set PROJECT_DESC=為寶貝專屬打造的馬卡龍粉色系計畫書，包含打卡流程與各種溫馨任務清單。
set EXEC_FILE=%CWD%\main.py

echo Registering "%PROJECT_NAME%" to AI Tool Launcher...
if exist "g:\python\toolLauncher\core\register_api.py" (
    python "g:\python\toolLauncher\core\register_api.py" --name "%PROJECT_NAME%" --desc "%PROJECT_DESC%" --exec "%EXEC_FILE%" --cwd "%CWD%"
) else if exist "g:\python\toolLauncher\register_api.py" (
    python "g:\python\toolLauncher\register_api.py" --name "%PROJECT_NAME%" --desc "%PROJECT_DESC%" --exec "%EXEC_FILE%" --cwd "%CWD%"
) else (
    echo Error: Could not find register_api.py in toolLauncher.
)

echo.
echo Registration complete! You can now close this window.
pause
