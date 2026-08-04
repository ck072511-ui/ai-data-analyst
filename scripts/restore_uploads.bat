@echo off
REM ==============================================================================
REM AI Data Analyst - Uploads Restore Windows Script
REM ==============================================================================

set UPLOADS_PATH=/app/data/uploads

REM Auto-detect running container
set CONTAINER_NAME=ai_analyst_prod_backend
docker ps --format "{{.Names}}" | findstr /I "ai_analyst_prod_backend" >nul
if %errorlevel% neq 0 (
    docker ps --format "{{.Names}}" | findstr /I "ai_analyst_backend" >nul
    if %errorlevel% equ 0 (
        set CONTAINER_NAME=ai_analyst_backend
    )
)

if "%~1"=="" (
    echo Usage: %0 ^<path_to_uploads_backup.tar.gz^>
    exit /b 1
)

set BACKUP_FILE=%~1

if not exist "%BACKUP_FILE%" (
    echo Error: Backup file not found at: %BACKUP_FILE%
    exit /b 1
)

echo ======================================================================
echo Starting Uploads Restore (Windows)...
echo Container: %CONTAINER_NAME%
echo Path:      %UPLOADS_PATH%
echo Source:    %BACKUP_FILE%
echo ======================================================================

docker exec -i %CONTAINER_NAME% tar -xzf - -C %UPLOADS_PATH% < "%BACKUP_FILE%"

echo ----------------------------------------------------------------------
echo Uploads Restore Completed Successfully!
echo ======================================================================
pause
