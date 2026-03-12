@echo off
rem Backwards-compatible wrapper; delegates to the canonical script under scripts\.
call "%~dp0scripts\run_demo.bat" %*
