@echo off
chcp 1251 >nul
REM ============================================
REM  J.A.R.V.I.S. - zapusk aydenta (glavnaya knopka)
REM  Dvoynoy klik. Esli pishiut otnositel'no puti -
REM  snachala zapustite setup.bat
REM ============================================
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% gui.py
if %errorlevel% neq 0 (
  echo.
  echo Ne zapustilos. Skorye vsego, ne ustanovleny biblioteki,
  echo ili na kompyutere net Python. Zapustite setup.bat i povtorite.
  pause
)
