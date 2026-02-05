@echo off
setlocal enabledelayedexpansion

set JETSON_IP=192.168.0.104
set USERNAME=nvidia

echo === Jetson Deployment Script ===
echo.

echo Connecting to Jetson at %JETSON_IP%...
echo.

(
echo cd ~/edge_infer
echo git merge --abort 2^>^/dev/null ^|^| true
echo git reset --hard origin/master
echo echo === Cleaning build directory ===
echo rm -rf build
echo mkdir build && cd build
echo echo === Running CMake ===
echo cmake .. -DUSE_TENSORRT=ON
echo echo === Compiling ===
echo make -j4 2^>^&1 ^| tee compile.log
echo echo === Checking result ===
echo ls -la edge_framework
echo echo === DONE ===
) | "C:\Windows\System32\OpenSSH\ssh.exe" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null %USERNAME%@%JETSON_IP%

echo.
echo === Script Complete ===
pause
