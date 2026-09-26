@echo off
setlocal EnableExtensions EnableDelayedExpansion

title KARUME SYSTEM LAUNCHER

set "BASE=C:\Users\mr-karume\Desktop\messages"
set "VENV=%BASE%\virual"
set "STORE=%BASE%\KarumeStore"
set "PYTHON=%VENV%\Scripts\python.exe"

echo.
echo ==========================================
echo        KARUME SYSTEM LAUNCHER
echo ==========================================
echo.


REM =========================================================
REM CHECK PYTHON
REM =========================================================

if not exist "%PYTHON%" (
    echo [ERROR] Python virtual environment not found.
    echo Expected:
    echo %PYTHON%
    echo.
    pause
    exit /b 1
)


REM =========================================================
REM 1. KARUMESMS - PORT 5001
REM =========================================================

echo [1/3] Checking KarumeSMS - Port 5001...

netstat -ano | findstr ":5001" | findstr "LISTENING" >nul

if %errorlevel%==0 (

    echo [OK] KarumeSMS is already running.

) else (

    echo [START] Starting KarumeSMS...

    start "KarumeSMS - Port 5001" cmd /k "cd /d %BASE% && %PYTHON% app.py"

    echo [WAIT] Waiting for KarumeSMS...

    timeout /t 3 /nobreak >nul

    netstat -ano | findstr ":5001" | findstr "LISTENING" >nul

    if %errorlevel%==0 (
        echo [OK] KarumeSMS started successfully.
    ) else (
        echo [ERROR] KarumeSMS failed to start.
    )

)

echo.


REM =========================================================
REM 2. SMS WORKER
REM =========================================================

echo [2/3] Checking SMS Worker...

tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >nul

if %errorlevel%==0 (

    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*sms_worker.py*' }; if ($p) { exit 0 } else { exit 1 }"

    if !errorlevel!==0 (

        echo [OK] SMS Worker is already running.

    ) else (

        echo [START] Starting SMS Worker...

        start "KarumeSMS SMS Worker" cmd /k "cd /d %BASE% && %PYTHON% sms_worker.py"

        timeout /t 2 /nobreak >nul

        echo [OK] SMS Worker started.

    )

) else (

    echo [START] Starting SMS Worker...

    start "KarumeSMS SMS Worker" cmd /k "cd /d %BASE% && %PYTHON% sms_worker.py"

    timeout /t 2 /nobreak >nul

    echo [OK] SMS Worker started.

)

echo.


REM =========================================================
REM 3. KARUMESTORE - PORT 5000
REM =========================================================

echo [3/3] Checking KarumeStore - Port 5000...

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul

if %errorlevel%==0 (

    echo [OK] KarumeStore is already running.

) else (

    echo [START] Starting KarumeStore...

    start "KarumeStore - Port 5000" cmd /k "cd /d %STORE% && %PYTHON% app.py"

    echo [WAIT] Waiting for KarumeStore...

    timeout /t 3 /nobreak >nul

    netstat -ano | findstr ":5000" | findstr "LISTENING" >nul

    if %errorlevel%==0 (
        echo [OK] KarumeStore started successfully.
    ) else (
        echo [ERROR] KarumeStore failed to start.
    )

)

echo.
echo.
echo ==========================================
echo         KARUME SYSTEM STATUS
echo ==========================================
echo.


REM =========================================================
REM FINAL STATUS - KARUMESMS
REM =========================================================

netstat -ano | findstr ":5001" | findstr "LISTENING" >nul

if %errorlevel%==0 (
    echo [ONLINE] KarumeSMS - Port 5001
) else (
    echo [OFFLINE] KarumeSMS - Port 5001
)


REM =========================================================
REM FINAL STATUS - SMS WORKER
REM =========================================================

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"$p = Get-CimInstance Win32_Process -Filter \"Name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*sms_worker.py*' }; if ($p) { Write-Host '[ONLINE] SMS Worker' } else { Write-Host '[OFFLINE] SMS Worker' }"


REM =========================================================
REM FINAL STATUS - KARUMESTORE
REM =========================================================

netstat -ano | findstr ":5000" | findstr "LISTENING" >nul

if %errorlevel%==0 (
    echo [ONLINE] KarumeStore - Port 5000
) else (
    echo [OFFLINE] KarumeStore - Port 5000
)


echo.
echo ==========================================
echo       KARUME SYSTEM READY
echo ==========================================
echo.
echo KarumeSMS : http://127.0.0.1:5001
echo KarumeStore: http://127.0.0.1:5000
echo.
pause