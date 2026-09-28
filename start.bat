@echo off
chcp 1251 >nul
REM ============================================
REM  J.A.R.V.I.S. - zapusk (glavnaya knopka)
REM  Rabotaet v izolirovannom okruzhenii .venv -
REM  sistemnyi Python ne ispol'zuetsya vovse.
REM  Esli .venv net - snachala zapustite setup.bat
REM ============================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Ne naydeno okruzhenie .venv.
  echo Snachala odin raz zapustite setup.bat - on sozdet ego sam.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" gui.py %*
if %errorlevel% neq 0 (
  echo.
  echo Ne zapustilos. Tekshche oshibki vyshe.
  echo Esli ne pomogaet - zapustite setup.bat povtorno.
  pause
)
