@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0\myapp\deploy"

REM Array of Dockerfile names
set "services=debian.base.Dockerfile 1-service.Dockerfile 2-service.Dockerfile 3-service.Dockerfile 4-service.Dockerfile 6-service.Dockerfile"

REM Build Docker Images in Order
for %%s in (%services%) do (
    set "errorCount=0"
    :build
    docker build --no-cache -t %%~ns:latest -f %%s .
    if errorlevel 1 (
        set /a errorCount+=1
        if !errorCount! lss 2 (
            echo Docker build failed for %%s, retrying...
            goto build
        ) else (
            echo Docker build failed for %%s twice, aborting.
            exit /b 1
        )
    )
)

REM Change directory to run docker-compose
cd ..
docker-compose up --build
