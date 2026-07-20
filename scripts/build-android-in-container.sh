#!/usr/bin/env bash
set -euo pipefail

cd /workspace/android
gradle --no-daemon --stacktrace testDebugUnitTest assembleDebug

mkdir -p /workspace/dist
cp app/build/outputs/apk/debug/app-debug.apk /workspace/dist/hg-client-debug.apk
sha256sum /workspace/dist/hg-client-debug.apk
