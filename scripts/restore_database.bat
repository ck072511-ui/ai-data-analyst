@echo off
REM ==============================================================================
REM AI Data Analyst - PostgreSQL Restore Windows Script
REM ==============================================================================

set DB_USER=analyst
set DB_NAME=analytics_db

REM Auto-detect running container
set CONTAINER_NAME=ai_analyst_prod_db
docker ps --format "{{.Names}}" | findstr /I "ai_analyst_prod_db" >nul
if %errorlevel% neq 0 (
    docker ps --format "{{.Names}}" | findstr /I "ai_analyst_db" >nul
    if %errorlevel% equ 0 (
        set CONTAINER_NAME=ai_analyst_db
    )
)

if "%~1"=="" (
    echo Usage: %0 ^<path_to_backup_file.sql^>
    exit /b 1
)

set BACKUP_FILE=%~1

if not exist "%BACKUP_FILE%" (
    echo Error: Backup file not found at: %BACKUP_FILE%
    exit /b 1
)

echo ======================================================================
echo Starting PostgreSQL Database Restore (Windows)...
echo Container: %CONTAINER_NAME%
echo Database:  %DB_NAME%
echo Source:    %BACKUP_FILE%
echo ======================================================================

docker exec -i %CONTAINER_NAME% psql -U %DB_USER% -d %DB_NAME% < "%BACKUP_FILE%"

echo ----------------------------------------------------------------------
echo Database Restore Completed Successfully!
echo ======================================================================
pause
