@echo off
rem Bien dich chuong trinh C that (ban loi v0 va ban sua v1) bang gcc tren Windows.
cd /d %~dp0
if not exist build mkdir build
gcc -O0 -g -o build\tt_v0.exe thanhtoan.c || exit /b 1
gcc -O0 -g -DV1 -o build\tt_v1.exe thanhtoan.c || exit /b 1
echo Da bien dich build\tt_v0.exe va build\tt_v1.exe
