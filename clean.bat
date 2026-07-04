@echo off
echo Cleaning build directories...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q .pytest_cache 2>nul
del /q *.spec 2>nul
echo Clean complete.
