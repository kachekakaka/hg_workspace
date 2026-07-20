@echo off
setlocal
docker compose --profile build run --rm android-builder
if errorlevel 1 exit /b %errorlevel%
echo APK: dist\hg-client-debug.apk
