@echo off
setlocal
where adb >nul 2>nul
if errorlevel 1 (
  echo adb not found. Install the portable Android Platform-Tools or copy the APK manually.
  exit /b 1
)
if not exist dist\hg-client-debug.apk (
  echo dist\hg-client-debug.apk not found. Run scripts\build-apk.bat first.
  exit /b 1
)
adb install -r dist\hg-client-debug.apk
