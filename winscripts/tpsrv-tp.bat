@echo off

set tpfile=%~1

if not defined tpfile (
  echo TP file must be specified as first argument
  exit /b 1
)

for %%a in ("%tpfile%") do set "tpfile=%%~fa"

if not exist "%tpfile%" (
  echo TP file %tpfile% does not exist, first argument must be a TP file
  exit /b 1
)

tpsrv -v squore post --url http://tc/tp/tournament tp "%tpfile%

pause
