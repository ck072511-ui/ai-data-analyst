@echo off
REM ==============================================================================
REM AI Data Analyst - PostgreSQL Backup Windows Script
REM ==============================================================================

set BACKUP_DIR=.\backups
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

REM Robust locale-independent timestamp generation using PowerShell
for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"`) do set TIMESTAMP=%%i
set BACKUP_FILE=%BACKUP_DIR%\postgres_backup_%TIMESTAMP%.sql

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo ======================================================================
echo Starting PostgreSQL Database Backup (Windows)...
echo Container: %CONTAINER_NAME%
echo Database:  %DB_NAME%
echo Target:    %BACKUP_FILE%
echo ======================================================================

docker exec -t %CONTAINER_NAME% pg_dump -U %DB_USER% %DB_NAME% > "%BACKUP_FILE%"

echo ----------------------------------------------------------------------
echo Backup Completed Successfully!
echo ======================================================================
pause
